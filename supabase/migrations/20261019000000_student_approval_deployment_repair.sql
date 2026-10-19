-- Student registration approval deployment repair.
-- This focused migration can also be run on an existing project whose B05
-- invitation changes have not been deployed. It touches only the approval
-- RPC and its audit idempotency key, preserving existing accounts and data.
-- Approval, institution-scoped role grant, and audit persist in one transaction.
BEGIN;

ALTER TABLE public.admin_audit_log ADD COLUMN IF NOT EXISTS decision_key text;
CREATE UNIQUE INDEX IF NOT EXISTS b05_decision_audit_key
    ON public.admin_audit_log(decision_key);

CREATE OR REPLACE FUNCTION public.b05_approve_student(
    p_student_id uuid, p_institution_id uuid, p_actor_user_id uuid, p_actor_auth_user_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_student public.students%ROWTYPE;
    v_org uuid;
    v_role uuid;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.institutions i ON i.institution_id = p_institution_id
        WHERE u.id = p_actor_user_id AND u.auth_user_id = p_actor_auth_user_id AND u.status = 'active'
          AND r.name IN ('admin','staff') AND r.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND ur.scope_organization_id = i.organization_id AND i.status = 'active' AND i.is_active
    ) THEN RAISE EXCEPTION 'Authorized student approver required' USING ERRCODE = '42501'; END IF;
    SELECT * INTO v_student FROM public.students
        WHERE student_id = p_student_id AND institution_id = p_institution_id FOR UPDATE;
    IF NOT FOUND THEN RETURN jsonb_build_object('not_found',true); END IF;
    IF v_student.approval_status NOT IN ('pending','approved') THEN
        RETURN jsonb_build_object('conflict',true);
    END IF;
    SELECT organization_id INTO v_org FROM public.institutions
        WHERE institution_id = p_institution_id AND status = 'active' AND is_active FOR SHARE;
    SELECT id INTO v_role FROM public.roles WHERE name = 'student' AND is_active FOR SHARE;
    PERFORM 1 FROM public.users WHERE id = v_student.user_id AND status = 'active'
        AND auth_user_id IS NOT NULL AND lower(email) = lower(v_student.email) FOR UPDATE;
    IF NOT FOUND OR v_role IS NULL OR v_org IS NULL THEN
        RAISE EXCEPTION 'Student provisioning prerequisites missing' USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.user_roles (user_id,role_id,scope_type,scope_id,scope_organization_id)
        VALUES (v_student.user_id,v_role,'institution',p_institution_id,v_org)
        ON CONFLICT (user_id,role_id) DO NOTHING;
    IF NOT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = v_student.user_id
        AND role_id = v_role AND scope_type = 'institution' AND scope_id = p_institution_id
        AND scope_organization_id = v_org) THEN
        RAISE EXCEPTION 'Student role scope conflict' USING ERRCODE = '42501';
    END IF;
    UPDATE public.students SET approval_status = 'approved' WHERE student_id = p_student_id RETURNING * INTO v_student;
    INSERT INTO public.admin_audit_log
        (actor_user_id,institution_id,action,table_name,record_id,record_data,status,decision_key)
        VALUES (p_actor_user_id,p_institution_id,'student.approve','students',p_student_id::text,
            jsonb_build_object('approval_status','approved','role_granted',true),'success','student:' || p_student_id::text)
        ON CONFLICT (decision_key) DO NOTHING;
    RETURN jsonb_build_object('student',to_jsonb(v_student),'role_granted',true,'audit_persisted',true);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_approve_student(uuid,uuid,uuid,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_approve_student(uuid,uuid,uuid,uuid) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;

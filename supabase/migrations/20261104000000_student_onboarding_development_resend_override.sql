-- Development-only student invitation resend override.
-- The backend supplies p_development_mode from its server-owned environment.
-- Clients cannot call this service-role function directly.
BEGIN;

ALTER TABLE public.student_onboarding_invitations
    DROP CONSTRAINT IF EXISTS student_onboarding_invitations_resend_window_count_check;
ALTER TABLE public.student_onboarding_invitations
    ADD CONSTRAINT student_onboarding_invitations_resend_window_count_check
    CHECK (resend_window_count >= 0);

DROP FUNCTION IF EXISTS public.resend_student_onboarding_invitation(
    uuid, uuid, uuid, text, timestamptz
);

CREATE FUNCTION public.resend_student_onboarding_invitation(
    p_actor uuid,
    p_tenant uuid,
    p_invitation uuid,
    p_token_hash text,
    p_expires_at timestamptz,
    p_development_mode boolean DEFAULT false
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    row public.student_onboarding_invitations;
    now_at timestamptz := clock_timestamp();
    section_row jsonb;
    batch_code text;
    institution_name text;
BEGIN
    PERFORM public.assert_semester_registration_admin(
        p_actor, p_tenant, 'students.create'
    );
    SELECT * INTO row
    FROM public.student_onboarding_invitations
    WHERE invitation_id = p_invitation
      AND institution_id = p_tenant
      AND status = 'pending'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE = 'P0002';
    END IF;
    IF row.resend_window_started_at IS NULL
       OR row.resend_window_started_at <= now_at - interval '1 hour' THEN
        row.resend_window_started_at := now_at;
        row.resend_window_count := 0;
    END IF;
    IF NOT COALESCE(p_development_mode, false) AND row.resend_window_count >= 3 THEN
        RAISE EXCEPTION 'Student invitation resend limit reached' USING ERRCODE = 'P0001';
    END IF;
    IF p_token_hash IS NULL OR p_token_hash !~ '^[0-9a-f]{64}$'
       OR p_expires_at IS NULL OR p_expires_at <= now_at
       OR p_expires_at > now_at + interval '10 minutes' THEN
        RAISE EXCEPTION 'Invalid student invitation token' USING ERRCODE = '22023';
    END IF;
    UPDATE public.student_onboarding_invitations
    SET token_hash = p_token_hash,
        expires_at = p_expires_at,
        email_delivery_status = 'pending',
        resend_window_started_at = row.resend_window_started_at,
        resend_window_count = CASE
            WHEN COALESCE(p_development_mode, false) THEN 0
            ELSE row.resend_window_count + 1
        END,
        updated_at = now_at
    WHERE invitation_id = p_invitation
    RETURNING * INTO row;
    INSERT INTO public.admin_audit_log(
        actor_user_id, institution_id, action, table_name, record_id, record_data, status
    ) VALUES (
        p_actor, p_tenant, 'student.invitation.resent',
        'student_onboarding_invitations', row.invitation_id::text,
        jsonb_build_object('expires_at', p_expires_at), 'success'
    );
    section_row := public.academic_structure_parent(
        'academic_sections', row.academic_section_id, p_tenant
    );
    SELECT code INTO batch_code FROM public.admission_cohorts
    WHERE admission_cohort_id = (section_row ->> 'admission_cohort_id')::uuid;
    SELECT name INTO institution_name FROM public.institutions
    WHERE institution_id = p_tenant;
    RETURN to_jsonb(row) || jsonb_build_object(
        'section_name', section_row ->> 'name',
        'section_code', section_row ->> 'code',
        'batch_code', batch_code,
        'institution_name', institution_name
    );
END;
$$;

REVOKE ALL ON FUNCTION public.resend_student_onboarding_invitation(
    uuid, uuid, uuid, text, timestamptz, boolean
) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.resend_student_onboarding_invitation(
    uuid, uuid, uuid, text, timestamptz, boolean
) TO service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;

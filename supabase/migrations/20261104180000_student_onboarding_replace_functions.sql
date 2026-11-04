-- Idempotent replacement of all student onboarding functions.
-- Safe to run when the table already exists (skips CREATE TABLE).
-- Apply after 20261101000000_student_onboarding.sql fails with 42P07.
BEGIN;

CREATE OR REPLACE FUNCTION public.create_student_onboarding_invitation(
    p_actor uuid, p_tenant uuid, p_email text, p_student_name text,
    p_register_number text, p_university_roll_number text, p_section uuid,
    p_token_hash text, p_expires_at timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row public.student_onboarding_invitations; section_row jsonb; batch_code text;
    institution_name text;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.approve');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'courses.manage');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.update');
    IF p_email IS NULL OR length(btrim(p_email)) NOT BETWEEN 3 AND 320
        OR p_student_name IS NULL OR length(btrim(p_student_name)) NOT BETWEEN 1 AND 200
        OR p_register_number IS NULL OR length(btrim(p_register_number)) NOT BETWEEN 1 AND 128
        OR (p_university_roll_number IS NOT NULL AND length(btrim(p_university_roll_number)) NOT BETWEEN 1 AND 128)
        OR p_token_hash IS NULL OR p_token_hash !~ '^[0-9a-f]{64}$'
        OR p_expires_at IS NULL OR p_expires_at <= now()
        OR p_expires_at > now()+interval '10 minutes' THEN
        RAISE EXCEPTION 'Invalid student invitation' USING ERRCODE='22023';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    section_row:=public.academic_structure_parent('academic_sections',p_section,p_tenant);
    IF EXISTS (SELECT 1 FROM public.users WHERE lower(email)=lower(btrim(p_email)))
        OR EXISTS (SELECT 1 FROM auth.users WHERE lower(email)=lower(btrim(p_email)))
        OR EXISTS (SELECT 1 FROM public.students WHERE institution_id=p_tenant
            AND (lower(email)=lower(btrim(p_email))
                OR lower(btrim(register_number))=lower(btrim(p_register_number))
                OR (p_university_roll_number IS NOT NULL
                    AND lower(btrim(university_roll_number))=lower(btrim(p_university_roll_number))))) THEN
        RAISE EXCEPTION 'Student identity already exists' USING ERRCODE='23505';
    END IF;
    INSERT INTO public.student_onboarding_invitations
        (institution_id,email,student_name,register_number,university_roll_number,
         academic_section_id,token_hash,expires_at,created_by)
    VALUES (p_tenant,lower(btrim(p_email)),btrim(p_student_name),btrim(p_register_number),
        nullif(btrim(p_university_roll_number),''),p_section,p_token_hash,p_expires_at,p_actor)
    RETURNING * INTO row;
    SELECT code INTO batch_code FROM public.admission_cohorts
    WHERE admission_cohort_id=(section_row->>'admission_cohort_id')::uuid;
    SELECT name INTO institution_name FROM public.institutions WHERE institution_id=p_tenant;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES (p_actor,p_tenant,'student.invitation.created','student_onboarding_invitations',
        row.invitation_id::text,jsonb_build_object('email',row.email,'register_number',row.register_number,
        'academic_section_id',p_section), 'success');
    RETURN to_jsonb(row)||jsonb_build_object('section_name',section_row->>'name',
        'section_code',section_row->>'code','batch_code',batch_code,
        'institution_name',institution_name);
END;
$$;

CREATE OR REPLACE FUNCTION public.read_student_onboarding_invitations(p_actor uuid,p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.read');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    SELECT coalesce(jsonb_agg(jsonb_build_object(
        'invitation_id',i.invitation_id,'institution_id',i.institution_id,'email',i.email,
        'student_name',i.student_name,'register_number',i.register_number,
        'university_roll_number',i.university_roll_number,'academic_section_id',i.academic_section_id,
        'section_name',s.name,'section_code',s.code,'batch_name',c.name,'batch_code',c.code,
        'status',i.status,'expires_at',i.expires_at,'created_at',i.created_at,
        'email_delivery_status',i.email_delivery_status,'email_delivery_attempts',i.email_delivery_attempts,
        'resend_count',i.resend_window_count,'last_sent_at',i.last_sent_at
    ) ORDER BY i.created_at DESC),'[]'::jsonb) INTO result
    FROM public.student_onboarding_invitations i
    JOIN public.academic_sections s ON s.academic_section_id = i.academic_section_id
    JOIN public.admission_cohorts c ON c.admission_cohort_id = s.admission_cohort_id
    WHERE i.institution_id=p_tenant AND i.status='pending';
    RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION public.reassign_student_onboarding_section(
    p_actor uuid,p_tenant uuid,p_invitation uuid,p_section uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row public.student_onboarding_invitations;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'courses.manage');
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    PERFORM public.academic_structure_parent('academic_sections',p_section,p_tenant);
    UPDATE public.student_onboarding_invitations SET academic_section_id=p_section,updated_at=now()
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND status='pending'
    RETURNING * INTO row;
    IF NOT FOUND THEN RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002'; END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.section_reassigned','student_onboarding_invitations',
        row.invitation_id::text,jsonb_build_object('academic_section_id',p_section),'success');
    RETURN to_jsonb(row);
END;
$$;

CREATE OR REPLACE FUNCTION public.record_student_onboarding_delivery(
    p_actor uuid,p_tenant uuid,p_invitation uuid,p_token_hash text,p_status text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row public.student_onboarding_invitations;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    IF p_status NOT IN ('sent','failed') THEN RAISE EXCEPTION 'Invalid delivery status' USING ERRCODE='22023'; END IF;
    UPDATE public.student_onboarding_invitations
    SET email_delivery_status=p_status,email_delivery_attempts=email_delivery_attempts+1,
        last_sent_at=CASE WHEN p_status='sent' THEN now() ELSE last_sent_at END,updated_at=now()
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND token_hash=p_token_hash AND status='pending'
    RETURNING * INTO row;
    IF NOT FOUND THEN RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002'; END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.email_'||p_status,'student_onboarding_invitations',
        row.invitation_id::text,jsonb_build_object('delivery_status',p_status),'success');
    RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION public.record_student_onboarding_auth_user(
    p_invitation uuid,p_token_hash text,p_auth_user uuid
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE invite public.student_onboarding_invitations; auth_email text; app_meta jsonb;
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    SELECT * INTO invite FROM public.student_onboarding_invitations
    WHERE invitation_id=p_invitation AND token_hash=p_token_hash AND status='pending'
        AND expires_at>clock_timestamp() FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student setup link is expired or unavailable' USING ERRCODE='P0002'; END IF;
    SELECT email,raw_app_meta_data INTO auth_email,app_meta FROM auth.users WHERE id=p_auth_user FOR SHARE;
    IF auth_email IS NULL OR lower(auth_email)<>lower(invite.email)
        OR app_meta->>'student_onboarding_invitation_id'<>invite.invitation_id::text THEN
        RAISE EXCEPTION 'Student email verification is not valid' USING ERRCODE='42501';
    END IF;
    UPDATE public.student_onboarding_invitations SET provisioned_auth_user_id=p_auth_user,updated_at=now()
    WHERE invitation_id=p_invitation AND (provisioned_auth_user_id IS NULL OR provisioned_auth_user_id=p_auth_user);
    IF NOT FOUND THEN RAISE EXCEPTION 'Student invitation account mismatch' USING ERRCODE='42501'; END IF;
    RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION public.inspect_student_onboarding_invitation(p_token_hash text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row jsonb;
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    SELECT jsonb_build_object('invitation_id',i.invitation_id,'student_name',i.student_name,
        'email',i.email,'institution_id',i.institution_id,'expires_at',i.expires_at,
        'status',i.status,'academic_section_id',i.academic_section_id,
        'section_name',s.name,'section_active',s.is_active AND c.is_active AND ps.is_active AND term.is_active,
        'batch_name',c.name,'batch_code',c.code,'institution_name',inst.name)
        || jsonb_build_object('provisioned_auth_user_id',coalesce(i.provisioned_auth_user_id,
            (SELECT u.id FROM auth.users u WHERE lower(u.email)=lower(i.email)
                AND u.raw_app_meta_data->>'student_onboarding_invitation_id'=i.invitation_id::text
                ORDER BY u.created_at DESC LIMIT 1)))
    INTO row FROM public.student_onboarding_invitations i
    JOIN public.academic_sections s ON s.academic_section_id = i.academic_section_id
    JOIN public.admission_cohorts c ON c.admission_cohort_id = s.admission_cohort_id
    JOIN public.program_semesters ps ON ps.program_semester_id = s.program_semester_id
    JOIN public.semesters term ON term.semester_id = s.semester_id
    JOIN public.institutions inst ON inst.institution_id = i.institution_id
    WHERE i.token_hash=p_token_hash AND (i.status='accepted' OR (i.status='pending' AND i.expires_at>now()));
    RETURN row;
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_student_onboarding_invitation(
    p_invitation uuid,p_token_hash text,p_auth_user uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE invite public.student_onboarding_invitations; auth_email text; auth_verified timestamptz;
    app_meta jsonb;
    public_user uuid; student uuid; first_name text; last_name text; approval jsonb; assignment jsonb;
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    SELECT * INTO invite FROM public.student_onboarding_invitations
    WHERE invitation_id=p_invitation AND token_hash=p_token_hash FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student setup link is invalid' USING ERRCODE='P0002'; END IF;
    IF invite.status='accepted' AND invite.accepted_auth_user_id=p_auth_user THEN
        RETURN jsonb_build_object('accepted',true,'student_id',invite.student_id,'user_id',invite.accepted_user_id);
    END IF;
    IF invite.status<>'pending' OR invite.expires_at<=clock_timestamp() THEN
        RAISE EXCEPTION 'Student setup link is expired or unavailable' USING ERRCODE='P0002';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||invite.institution_id::text,0));
    PERFORM public.academic_structure_parent('academic_sections',invite.academic_section_id,invite.institution_id);
    IF invite.provisioned_auth_user_id IS DISTINCT FROM p_auth_user THEN
        RAISE EXCEPTION 'Student invitation account is not associated' USING ERRCODE='42501';
    END IF;
    SELECT email,email_confirmed_at,raw_app_meta_data
    INTO auth_email,auth_verified,app_meta FROM auth.users WHERE id=p_auth_user FOR SHARE;
    IF auth_email IS NULL OR lower(auth_email)<>lower(invite.email) OR auth_verified IS NULL
        OR app_meta->>'student_onboarding_invitation_id'<>invite.invitation_id::text THEN
        RAISE EXCEPTION 'Student email verification is not valid' USING ERRCODE='42501';
    END IF;
    first_name:=split_part(btrim(invite.student_name),' ',1);
    last_name:=btrim(substr(btrim(invite.student_name),length(first_name)+1));
    INSERT INTO public.users(auth_user_id,email,first_name,last_name,display_name,status)
    VALUES(p_auth_user,invite.email,first_name,last_name,invite.student_name,'active')
    ON CONFLICT (auth_user_id) DO NOTHING;
    SELECT id INTO public_user FROM public.users WHERE auth_user_id=p_auth_user AND lower(email)=lower(invite.email) FOR UPDATE;
    IF public_user IS NULL THEN RAISE EXCEPTION 'Student account already belongs to another identity' USING ERRCODE='23505'; END IF;
    INSERT INTO public.students(user_id,institution_id,student_number,email,register_number,university_roll_number,
        approval_status,enrollment_date,status,is_active)
    VALUES(public_user,invite.institution_id,invite.register_number,invite.email,invite.register_number,
        invite.university_roll_number,'pending',current_date,'active',true)
    ON CONFLICT (user_id) DO NOTHING
    RETURNING student_id INTO student;
    IF student IS NULL THEN
        SELECT student_id INTO student FROM public.students WHERE user_id=public_user AND institution_id=invite.institution_id;
        IF student IS NULL THEN RAISE EXCEPTION 'Student profile belongs to another institution' USING ERRCODE='23505'; END IF;
    END IF;
    SELECT public.b05_approve_student(student,invite.institution_id,invite.created_by,
        (SELECT auth_user_id FROM public.users WHERE id=invite.created_by)) INTO approval;
    IF coalesce((approval->>'role_granted')::boolean,false) IS NOT TRUE THEN
        RAISE EXCEPTION 'Student activation requires administrator reconciliation' USING ERRCODE='42501';
    END IF;
    SELECT public.assign_student_semester(invite.created_by,invite.institution_id,student,
        invite.academic_section_id) INTO assignment;
    UPDATE public.student_onboarding_invitations SET status='accepted',accepted_auth_user_id=p_auth_user,
        accepted_user_id=public_user,student_id=student,updated_at=now()
    WHERE invitation_id=invite.invitation_id;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(invite.created_by,invite.institution_id,'student.invitation.accepted','student_onboarding_invitations',
        invite.invitation_id::text,jsonb_build_object('student_id',student,'academic_section_id',invite.academic_section_id),
        'success');
    RETURN jsonb_build_object('accepted',true,'student_id',student,'user_id',public_user,
        'semester_assignment',assignment);
END;
$$;

CREATE OR REPLACE FUNCTION public.update_student_onboarding_invitation(
    p_actor uuid, p_tenant uuid, p_invitation uuid,
    p_email text, p_student_name text, p_register_number text,
    p_university_roll_number text, p_section uuid,
    p_token_hash text, p_expires_at timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row public.student_onboarding_invitations; section_row jsonb; batch_code text; institution_name text;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.update');
    IF p_email IS NULL OR length(btrim(p_email)) NOT BETWEEN 3 AND 320
        OR p_student_name IS NULL OR length(btrim(p_student_name)) NOT BETWEEN 1 AND 200
        OR p_register_number IS NULL OR length(btrim(p_register_number)) NOT BETWEEN 1 AND 128
        OR (p_university_roll_number IS NOT NULL AND length(btrim(p_university_roll_number)) NOT BETWEEN 1 AND 128)
        OR p_token_hash IS NULL OR p_token_hash !~ '^[0-9a-f]{64}$'
        OR p_expires_at IS NULL OR p_expires_at <= now()
        OR p_expires_at > now()+interval '10 minutes' THEN
        RAISE EXCEPTION 'Invalid student invitation' USING ERRCODE='22023';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    IF p_section IS NOT NULL THEN
        section_row:=public.academic_structure_parent('academic_sections',p_section,p_tenant);
    END IF;
    UPDATE public.student_onboarding_invitations
    SET email=lower(btrim(p_email)), student_name=btrim(p_student_name),
        register_number=btrim(p_register_number),
        university_roll_number=nullif(btrim(p_university_roll_number),''),
        academic_section_id=COALESCE(p_section,academic_section_id),
        token_hash=p_token_hash, expires_at=p_expires_at,
        email_delivery_status='pending', updated_at=now()
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND status='pending'
    RETURNING * INTO row;
    IF NOT FOUND THEN RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002'; END IF;
    IF section_row IS NULL THEN
        SELECT jsonb_build_object('name',s.name,'code',s.code,'admission_cohort_id',s.admission_cohort_id)
        INTO section_row FROM public.academic_sections s WHERE s.academic_section_id=row.academic_section_id;
    END IF;
    SELECT code INTO batch_code FROM public.admission_cohorts
    WHERE admission_cohort_id=(section_row->>'admission_cohort_id')::uuid;
    SELECT name INTO institution_name FROM public.institutions WHERE institution_id=p_tenant;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.updated','student_onboarding_invitations',
        row.invitation_id::text,jsonb_build_object('email',row.email,'register_number',row.register_number),'success');
    RETURN to_jsonb(row)||jsonb_build_object('section_name',section_row->>'name',
        'section_code',section_row->>'code','batch_code',batch_code,'institution_name',institution_name);
END;
$$;

CREATE OR REPLACE FUNCTION public.cancel_student_onboarding_invitation(
    p_actor uuid,p_tenant uuid,p_invitation uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row public.student_onboarding_invitations;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    UPDATE public.student_onboarding_invitations SET status='cancelled',updated_at=now()
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND status='pending'
    RETURNING * INTO row;
    IF NOT FOUND THEN RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002'; END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.cancelled','student_onboarding_invitations',
        row.invitation_id::text,'{}'::jsonb,'success');
    RETURN to_jsonb(row);
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_student_onboarding_setup(p_invitation uuid,p_token_hash text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    UPDATE public.student_onboarding_invitations SET updated_at=now()
    WHERE invitation_id=p_invitation AND token_hash=p_token_hash AND status='pending'
        AND expires_at>clock_timestamp();
    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION public.release_student_onboarding_setup(p_invitation uuid,p_token_hash text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    UPDATE public.student_onboarding_invitations SET updated_at=now()
    WHERE invitation_id=p_invitation AND token_hash=p_token_hash AND status='pending';
    RETURN FOUND;
END;
$$;

-- Security: restrict all functions to service_role only
ALTER TABLE public.student_onboarding_invitations OWNER TO postgres;
ALTER TABLE public.student_onboarding_invitations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.student_onboarding_invitations FROM PUBLIC,anon,authenticated,service_role;

REVOKE ALL ON FUNCTION
    public.create_student_onboarding_invitation(uuid,uuid,text,text,text,text,uuid,text,timestamptz),
    public.read_student_onboarding_invitations(uuid,uuid),
    public.reassign_student_onboarding_section(uuid,uuid,uuid,uuid),
    public.record_student_onboarding_delivery(uuid,uuid,uuid,text,text),
    public.record_student_onboarding_auth_user(uuid,text,uuid),
    public.inspect_student_onboarding_invitation(text),
    public.complete_student_onboarding_invitation(uuid,text,uuid),
    public.update_student_onboarding_invitation(uuid,uuid,uuid,text,text,text,text,uuid,text,timestamptz),
    public.cancel_student_onboarding_invitation(uuid,uuid,uuid),
    public.claim_student_onboarding_setup(uuid,text),
    public.release_student_onboarding_setup(uuid,text)
FROM PUBLIC,anon,authenticated,service_role;

GRANT EXECUTE ON FUNCTION
    public.create_student_onboarding_invitation(uuid,uuid,text,text,text,text,uuid,text,timestamptz),
    public.read_student_onboarding_invitations(uuid,uuid),
    public.reassign_student_onboarding_section(uuid,uuid,uuid,uuid),
    public.record_student_onboarding_delivery(uuid,uuid,uuid,text,text),
    public.record_student_onboarding_auth_user(uuid,text,uuid),
    public.inspect_student_onboarding_invitation(text),
    public.complete_student_onboarding_invitation(uuid,text,uuid),
    public.update_student_onboarding_invitation(uuid,uuid,uuid,text,text,text,text,uuid,text,timestamptz),
    public.cancel_student_onboarding_invitation(uuid,uuid,uuid),
    public.claim_student_onboarding_setup(uuid,text),
    public.release_student_onboarding_setup(uuid,text)
TO service_role;

NOTIFY pgrst,'reload schema';
COMMIT;

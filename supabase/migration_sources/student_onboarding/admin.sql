CREATE FUNCTION public.create_student_onboarding_invitation(
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

CREATE FUNCTION public.read_student_onboarding_invitations(p_actor uuid,p_tenant uuid)
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
    JOIN public.academic_sections s USING (academic_section_id)
    JOIN public.admission_cohorts c USING (admission_cohort_id)
    WHERE i.institution_id=p_tenant AND i.status='pending';
    RETURN result;
END;
$$;

CREATE FUNCTION public.reassign_student_onboarding_section(
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

CREATE FUNCTION public.resend_student_onboarding_invitation(
    p_actor uuid,p_tenant uuid,p_invitation uuid,p_token_hash text,p_expires_at timestamptz
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE row public.student_onboarding_invitations; now_at timestamptz:=clock_timestamp();
    section_row jsonb; batch_code text; institution_name text;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.create');
    SELECT * INTO row FROM public.student_onboarding_invitations
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND status='pending' FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002'; END IF;
    IF row.resend_window_started_at IS NULL OR row.resend_window_started_at <= now_at-interval '1 hour' THEN
        row.resend_window_started_at:=now_at; row.resend_window_count:=0;
    END IF;
    IF row.resend_window_count>=3 THEN
        RAISE EXCEPTION 'Student invitation resend limit reached' USING ERRCODE='P0001';
    END IF;
    IF p_token_hash IS NULL OR p_token_hash !~ '^[0-9a-f]{64}$'
        OR p_expires_at IS NULL OR p_expires_at<=now_at
        OR p_expires_at>now_at+interval '10 minutes' THEN
        RAISE EXCEPTION 'Invalid student invitation token' USING ERRCODE='22023';
    END IF;
    UPDATE public.student_onboarding_invitations SET token_hash=p_token_hash,expires_at=p_expires_at,
        email_delivery_status='pending',resend_window_started_at=row.resend_window_started_at,
        resend_window_count=row.resend_window_count+1,updated_at=now_at
    WHERE invitation_id=p_invitation RETURNING * INTO row;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.resent','student_onboarding_invitations',
        row.invitation_id::text,jsonb_build_object('expires_at',p_expires_at),'success');
    section_row:=public.academic_structure_parent('academic_sections',row.academic_section_id,p_tenant);
    SELECT code INTO batch_code FROM public.admission_cohorts
    WHERE admission_cohort_id=(section_row->>'admission_cohort_id')::uuid;
    SELECT name INTO institution_name FROM public.institutions WHERE institution_id=p_tenant;
    RETURN to_jsonb(row)||jsonb_build_object('section_name',section_row->>'name',
        'section_code',section_row->>'code','batch_code',batch_code,
        'institution_name',institution_name);
END;
$$;

CREATE FUNCTION public.record_student_onboarding_delivery(
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

CREATE FUNCTION public.record_student_onboarding_auth_user(
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

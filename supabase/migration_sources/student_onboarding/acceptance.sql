CREATE FUNCTION public.inspect_student_onboarding_invitation(p_token_hash text)
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
    JOIN public.academic_sections s USING (academic_section_id)
    JOIN public.admission_cohorts c USING (admission_cohort_id)
    JOIN public.program_semesters ps USING (program_semester_id)
    JOIN public.semesters term USING (semester_id)
    JOIN public.institutions inst USING (institution_id)
    WHERE i.token_hash=p_token_hash AND (i.status='accepted' OR (i.status='pending' AND i.expires_at>now()));
    RETURN row;
END;
$$;

CREATE FUNCTION public.complete_student_onboarding_invitation(
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

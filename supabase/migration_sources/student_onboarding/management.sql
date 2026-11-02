CREATE FUNCTION public.update_student_onboarding_invitation(
    p_actor uuid,p_tenant uuid,p_invitation uuid,p_student_name text,
    p_register_number text,p_university_roll_number text,p_section uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE invite public.student_onboarding_invitations; before_row jsonb; result jsonb;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.update');
    IF p_section IS NOT NULL THEN
        PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'courses.manage');
    END IF;
    IF p_student_name IS NULL OR length(btrim(p_student_name)) NOT BETWEEN 1 AND 200
        OR p_register_number IS NULL OR length(btrim(p_register_number)) NOT BETWEEN 1 AND 128
        OR (p_university_roll_number IS NOT NULL
            AND length(btrim(p_university_roll_number)) NOT BETWEEN 1 AND 128) THEN
        RAISE EXCEPTION 'Invalid student invitation identity' USING ERRCODE='22023';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT * INTO invite FROM public.student_onboarding_invitations
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND status='pending'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.student_onboarding_invitations other
        WHERE other.institution_id=p_tenant AND other.status='pending'
            AND other.invitation_id<>p_invitation
            AND (lower(btrim(other.register_number))=lower(btrim(p_register_number))
                OR (p_university_roll_number IS NOT NULL
                    AND lower(btrim(other.university_roll_number))
                        =lower(btrim(p_university_roll_number))))
    ) OR EXISTS (
        SELECT 1 FROM public.students student
        WHERE student.institution_id=p_tenant
            AND (lower(btrim(student.register_number))=lower(btrim(p_register_number))
                OR lower(btrim(student.student_number))=lower(btrim(p_register_number))
                OR (p_university_roll_number IS NOT NULL
                    AND lower(btrim(student.university_roll_number))
                        =lower(btrim(p_university_roll_number))))
    ) THEN
        RAISE EXCEPTION 'Student identity already exists' USING ERRCODE='23505';
    END IF;
    IF p_section IS NOT NULL THEN
        PERFORM public.academic_structure_parent('academic_sections',p_section,p_tenant);
    END IF;
    before_row:=jsonb_build_object(
        'student_name',invite.student_name,'register_number',invite.register_number,
        'university_roll_number',invite.university_roll_number,
        'academic_section_id',invite.academic_section_id);
    UPDATE public.student_onboarding_invitations
    SET student_name=btrim(p_student_name),register_number=btrim(p_register_number),
        university_roll_number=nullif(btrim(p_university_roll_number),''), 
        academic_section_id=coalesce(p_section,academic_section_id),updated_at=now()
    WHERE invitation_id=p_invitation RETURNING * INTO invite;
    INSERT INTO public.admin_audit_log(
        actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.updated','student_onboarding_invitations',
        invite.invitation_id::text,jsonb_build_object('before',before_row,'after',jsonb_build_object(
            'student_name',invite.student_name,'register_number',invite.register_number,
            'university_roll_number',invite.university_roll_number,
            'academic_section_id',invite.academic_section_id)),'success');
    SELECT to_jsonb(invite)||jsonb_build_object(
        'section_name',section.name,'section_code',section.code,
        'batch_name',cohort.name,'batch_code',cohort.code)
    INTO result
    FROM public.academic_sections section
    JOIN public.admission_cohorts cohort USING (admission_cohort_id)
    WHERE section.academic_section_id=invite.academic_section_id;
    RETURN result;
END;
$$;

CREATE FUNCTION public.cancel_student_onboarding_invitation(
    p_actor uuid,p_tenant uuid,p_invitation uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE invite public.student_onboarding_invitations;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.delete');
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT * INTO invite FROM public.student_onboarding_invitations
    WHERE invitation_id=p_invitation AND institution_id=p_tenant AND status='pending'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pending student invitation not found' USING ERRCODE='P0002';
    END IF;
    IF invite.provisioned_auth_user_id IS NOT NULL OR EXISTS (
        SELECT 1 FROM auth.users auth_user
        WHERE auth_user.raw_app_meta_data->>'student_onboarding_invitation_id'
            =invite.invitation_id::text
    ) THEN
        RAISE EXCEPTION 'Student invitation setup has started' USING ERRCODE='P0003';
    END IF;
    UPDATE public.student_onboarding_invitations
    SET status='cancelled',updated_at=now()
    WHERE invitation_id=p_invitation;
    INSERT INTO public.admin_audit_log(
        actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.invitation.cancelled','student_onboarding_invitations',
        invite.invitation_id::text,jsonb_build_object('status','pending'),'success');
    RETURN jsonb_build_object('invitation_id',p_invitation,'cancelled',true);
END;
$$;

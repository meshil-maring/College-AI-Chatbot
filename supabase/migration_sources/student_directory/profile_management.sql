CREATE OR REPLACE FUNCTION public.update_admin_student_profile(
    p_actor uuid,p_tenant uuid,p_student uuid,p_student_name text,
    p_register_number text,p_university_roll_number text,p_section uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE student_row record; before_row jsonb; v_section_id uuid;
    v_first_name text; v_last_name text;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.update');
    IF p_section IS NOT NULL THEN
        PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'courses.manage');
    END IF;
    IF p_student_name IS NULL OR length(btrim(p_student_name)) NOT BETWEEN 1 AND 200
        OR p_register_number IS NULL OR length(btrim(p_register_number)) NOT BETWEEN 1 AND 128
        OR (p_university_roll_number IS NOT NULL
            AND length(btrim(p_university_roll_number)) NOT BETWEEN 1 AND 128) THEN
        RAISE EXCEPTION 'Invalid student identity' USING ERRCODE='22023';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT s.*,u.auth_user_id,u.first_name,u.last_name INTO student_row
    FROM public.students s JOIN public.users u ON u.id=s.user_id
    WHERE s.student_id=p_student AND s.institution_id=p_tenant
    FOR UPDATE OF s,u;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student not found' USING ERRCODE='P0002'; END IF;

    IF EXISTS (
        SELECT 1 FROM public.students other
        WHERE other.institution_id=p_tenant AND other.student_id<>p_student
          AND (lower(btrim(other.register_number))=lower(btrim(p_register_number))
            OR lower(btrim(other.student_number))=lower(btrim(p_register_number))
            OR (p_university_roll_number IS NOT NULL
                AND lower(btrim(other.university_roll_number))=lower(btrim(p_university_roll_number))))
    ) THEN
        RAISE EXCEPTION 'Student identity already exists' USING ERRCODE='23505';
    END IF;
    SELECT registration.academic_section_id INTO v_section_id
    FROM public.student_semester_registrations registration
    JOIN public.semesters term ON term.semester_id=registration.semester_id
    WHERE registration.student_id=p_student AND registration.institution_id=p_tenant
    ORDER BY term.start_date DESC,registration.assigned_at DESC,
        registration.semester_registration_id
    LIMIT 1;
    IF p_section IS NOT NULL THEN
        PERFORM public.assign_student_semester(p_actor,p_tenant,p_student,p_section);
    END IF;

    before_row:=jsonb_build_object(
        'student_name',concat_ws(' ',student_row.first_name,student_row.last_name),
        'register_number',student_row.register_number,
        'university_roll_number',student_row.university_roll_number,
        'academic_section_id',v_section_id);
    v_first_name:=split_part(btrim(p_student_name),' ',1);
    v_last_name:=btrim(substr(btrim(p_student_name),length(v_first_name)+1));
    UPDATE public.users SET first_name=v_first_name,last_name=v_last_name,
        display_name=btrim(p_student_name),updated_at=now()
    WHERE id=student_row.user_id;
    UPDATE public.students SET student_number=btrim(p_register_number),
        register_number=btrim(p_register_number),
        university_roll_number=nullif(btrim(p_university_roll_number),''),
        updated_at=now()
    WHERE student_id=p_student AND institution_id=p_tenant;
    SELECT registration.academic_section_id INTO v_section_id
    FROM public.student_semester_registrations registration
    JOIN public.semesters term ON term.semester_id=registration.semester_id
    WHERE registration.student_id=p_student AND registration.institution_id=p_tenant
    ORDER BY term.start_date DESC,registration.assigned_at DESC,
        registration.semester_registration_id
    LIMIT 1;

    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.profile.updated','students',p_student::text,
        jsonb_build_object('before',before_row,'after',jsonb_build_object(
            'student_name',btrim(p_student_name),'register_number',btrim(p_register_number),
            'university_roll_number',nullif(btrim(p_university_roll_number),''),
            'academic_section_id',v_section_id)),
        'success');
    RETURN jsonb_build_object('student_id',p_student,'updated',true);
END;
$$;

CREATE FUNCTION public.set_admin_student_active(
    p_actor uuid,p_tenant uuid,p_student uuid,p_active boolean
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE student_row public.students;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.update');
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT * INTO student_row FROM public.students
    WHERE student_id=p_student AND institution_id=p_tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student not found' USING ERRCODE='P0002'; END IF;
    IF p_active AND student_row.approval_status<>'approved' THEN
        RAISE EXCEPTION 'Only approved student accounts can be reactivated' USING ERRCODE='23514';
    END IF;
    IF student_row.status NOT IN ('active','inactive') THEN
        RAISE EXCEPTION 'Graduated or withdrawn student records cannot be reactivated here'
            USING ERRCODE='23514';
    END IF;
    IF student_row.is_active IS DISTINCT FROM p_active THEN
        UPDATE public.students SET is_active=p_active,
            status=CASE WHEN p_active THEN 'active' ELSE 'inactive' END,updated_at=now()
        WHERE student_id=p_student AND institution_id=p_tenant;
        INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
        VALUES(p_actor,p_tenant,CASE WHEN p_active THEN 'student.activated' ELSE 'student.deactivated' END,
            'students',p_student::text,jsonb_build_object(
                'before',jsonb_build_object('status',student_row.status,'is_active',student_row.is_active),
                'after',jsonb_build_object('status',CASE WHEN p_active THEN 'active' ELSE 'inactive' END,
                    'is_active',p_active)),'success');
    END IF;
    RETURN jsonb_build_object('student_id',p_student,'is_active',p_active);
END;
$$;

CREATE FUNCTION public.delete_unused_admin_student(
    p_actor uuid,p_tenant uuid,p_student uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE student_row public.students; dependency record; linked boolean;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.delete');
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT * INTO student_row FROM public.students
    WHERE student_id=p_student AND institution_id=p_tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student not found' USING ERRCODE='P0002'; END IF;

    FOR dependency IN
        SELECT child_schema.nspname AS schema_name,child_table.relname AS table_name,
            string_agg(format('child.%I=parent.%I',child_column.attname,parent_column.attname),
                ' AND ' ORDER BY keys.position) AS predicate
        FROM pg_catalog.pg_constraint fk
        JOIN pg_catalog.pg_class child_table ON child_table.oid=fk.conrelid
        JOIN pg_catalog.pg_namespace child_schema ON child_schema.oid=child_table.relnamespace
        CROSS JOIN LATERAL unnest(fk.conkey,fk.confkey)
            WITH ORDINALITY AS keys(child_number,parent_number,position)
        JOIN pg_catalog.pg_attribute child_column
            ON child_column.attrelid=fk.conrelid AND child_column.attnum=keys.child_number
        JOIN pg_catalog.pg_attribute parent_column
            ON parent_column.attrelid=fk.confrelid AND parent_column.attnum=keys.parent_number
        WHERE fk.contype='f' AND fk.confrelid=to_regclass('public.students')
        GROUP BY fk.oid,child_schema.nspname,child_table.relname
        ORDER BY child_schema.nspname,child_table.relname
    LOOP
        EXECUTE format(
            'SELECT EXISTS (SELECT 1 FROM %I.%I child JOIN public.students parent ON %s WHERE parent.student_id=$1)',
            dependency.schema_name,dependency.table_name,dependency.predicate)
        INTO linked USING p_student;
        IF linked THEN
            RAISE EXCEPTION 'Student has linked records' USING
                ERRCODE='P2003',DETAIL=dependency.table_name;
        END IF;
    END LOOP;

    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
    VALUES(p_actor,p_tenant,'student.profile.deleted','students',p_student::text,
        jsonb_build_object('before',jsonb_build_object(
            'student_id',p_student,'student_number',student_row.student_number,
            'register_number',student_row.register_number,
            'university_roll_number',student_row.university_roll_number,
            'user_id',student_row.user_id)),'success');
    DELETE FROM public.user_roles ur USING public.roles r
    WHERE ur.user_id=student_row.user_id AND ur.role_id=r.id AND r.name='student'
      AND ur.scope_type='institution' AND ur.scope_id=p_tenant;
    DELETE FROM public.students WHERE student_id=p_student AND institution_id=p_tenant;
    UPDATE public.users SET status='inactive',updated_at=now()
    WHERE id=student_row.user_id
      AND NOT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id=student_row.user_id);
    RETURN jsonb_build_object('student_id',p_student,'deleted',true);
END;
$$;

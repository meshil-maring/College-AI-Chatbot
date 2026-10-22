CREATE OR REPLACE FUNCTION public.commit_faculty_attendance_import(p_actor uuid, p_tenant uuid, p_import_id uuid,
    p_expected_updated_at timestamptz, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE item public.faculty_attendance_imports; ctx jsonb; row jsonb; data jsonb; identity jsonb; verified_identity jsonb;
    roster public.faculty_attendance_rosters; old public.faculty_attendance_rosters;
    count_rows integer := 0; attendance_date date; student uuid;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || p_tenant::text, 0));
    SELECT * INTO item FROM faculty_attendance_imports WHERE import_id = p_import_id AND institution_id = p_tenant FOR UPDATE;
    IF item.import_id IS NULL OR item.uploaded_by <> p_actor THEN RAISE EXCEPTION 'Import scope denied' USING ERRCODE = '42501'; END IF;
    ctx := assert_faculty_attendance_mutation(p_actor, p_tenant, item.section_id);
    IF item.status NOT IN ('VALIDATED','REVIEWED') OR item.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'Import changed or already committed' USING ERRCODE = '40001';
    END IF;
    IF jsonb_array_length(p_rows) NOT BETWEEN 1 AND 500 OR jsonb_array_length(p_rows) <>
        (SELECT count(*) FROM faculty_attendance_import_rows WHERE import_id = p_import_id AND row_number >= 2)
        OR EXISTS(SELECT 1 FROM faculty_attendance_import_rows WHERE import_id = p_import_id AND validation_status IN ('ERROR','DUPLICATE','CONFLICT')) THEN
        RAISE EXCEPTION 'Review errors remain' USING ERRCODE = '23514';
    END IF;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.review', 'faculty_attendance_imports', p_import_id::text,
        jsonb_build_object('validated_rows', jsonb_array_length(p_rows)), 'success');
    FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        IF row->'errors' <> '[]'::jsonb OR NOT EXISTS(SELECT 1 FROM faculty_attendance_import_rows
            WHERE import_id = p_import_id AND row_number = (row->>'row_number')::integer AND raw_data = row->'raw_data') THEN
            RAISE EXCEPTION 'Review changed' USING ERRCODE = '40001';
        END IF;
        data := row->'normalized_data';
        IF nullif(btrim(data->>'register_number'),'') IS NULL OR nullif(btrim(data->>'student_name'),'') IS NULL THEN
            RAISE EXCEPTION 'Missing identity' USING ERRCODE = '23514';
        END IF;
        SELECT * INTO old FROM faculty_attendance_rosters WHERE institution_id = p_tenant AND section_id = item.section_id
            AND register_number = data->>'register_number' FOR UPDATE;
        identity := faculty_attendance_identity(p_tenant, data->>'register_number', data->>'university_roll_number');
        IF old.roster_id IS NOT NULL AND NOT (identity->>'conflict')::boolean THEN
            verified_identity := public.academic_package_identity_for_roster(p_tenant, old.roster_id);
            IF identity->>'student_id' IS NOT DISTINCT FROM verified_identity->>'student_id' THEN
                identity := identity || jsonb_build_object('academic_year_id', verified_identity->>'academic_year_id');
            END IF;
        END IF;
        IF (identity->>'conflict')::boolean OR
            (identity->>'program_id' IS NOT NULL AND identity->>'program_id' <> ctx->>'program_id') OR
            (identity->>'academic_year_id' IS NOT NULL AND identity->>'academic_year_id' <> ctx->>'academic_year_id') THEN
            RAISE EXCEPTION 'Identity conflict' USING ERRCODE = '23514';
        END IF;
        student := CASE WHEN identity->>'approval_status' = 'approved' THEN (identity->>'student_id')::uuid ELSE NULL END;
        IF old.roster_id IS NOT NULL AND ((old.linked_student_id IS NOT NULL AND old.linked_student_id IS DISTINCT FROM student)
            OR (nullif(old.university_roll_number,'') IS NOT NULL AND nullif(data->>'university_roll_number','') IS NOT NULL
                AND old.university_roll_number <> data->>'university_roll_number')) THEN
            RAISE EXCEPTION 'Existing roster identity conflict' USING ERRCODE = '23514';
        END IF;
        IF old.roster_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM public.academic_class_subjects WHERE section_id = item.section_id
        ) THEN
            -- Updating existing evidence is permitted; an import cannot add a
            -- subject, reopen ended participation, or replace the package.
            UPDATE faculty_attendance_rosters SET student_name = data->>'student_name',
                email = COALESCE(NULLIF(data->>'email',''), old.email),
                university_roll_number = COALESCE(NULLIF(data->>'university_roll_number',''), old.university_roll_number),
                linked_student_id = COALESCE(old.linked_student_id, student),
                roster_status = CASE WHEN identity->>'student_id' IS NULL THEN 'UNREGISTERED'
                    WHEN student IS NULL THEN 'PENDING_APPROVAL'
                    WHEN identity->>'is_active' = 'true' AND identity->>'status' = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END,
                reconciliation_state = CASE WHEN student IS NOT NULL THEN 'LINKED'
                    WHEN identity->>'student_id' IS NOT NULL THEN 'PENDING' ELSE 'NONE' END,
                imported_summary = row->'imported_summary', source_metadata = jsonb_build_object('import_id', p_import_id)
            WHERE roster_id = old.roster_id RETURNING * INTO roster;
        ELSE
        INSERT INTO faculty_attendance_rosters(institution_id, section_id, course_offering_id, semester_id,
            register_number, university_roll_number, student_name, email, created_by, linked_student_id,
            roster_status, imported_summary, source_metadata, reconciliation_state)
        VALUES(p_tenant, item.section_id, item.course_offering_id, item.semester_id, data->>'register_number',
            nullif(data->>'university_roll_number',''), data->>'student_name', nullif(data->>'email',''), p_actor, student,
            CASE WHEN identity->>'student_id' IS NULL THEN 'UNREGISTERED' WHEN student IS NULL THEN 'PENDING_APPROVAL'
                 WHEN identity->>'is_active' = 'true' AND identity->>'status' = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END,
            row->'imported_summary', jsonb_build_object('import_id', p_import_id),
            CASE WHEN student IS NOT NULL THEN 'LINKED' WHEN identity->>'student_id' IS NOT NULL THEN 'PENDING' ELSE 'NONE' END)
        ON CONFLICT(institution_id, section_id, register_number) DO UPDATE SET
            university_roll_number = coalesce(EXCLUDED.university_roll_number, faculty_attendance_rosters.university_roll_number),
            student_name = EXCLUDED.student_name, email = coalesce(EXCLUDED.email, faculty_attendance_rosters.email),
            linked_student_id = coalesce(faculty_attendance_rosters.linked_student_id, EXCLUDED.linked_student_id),
            roster_status = EXCLUDED.roster_status, reconciliation_state = EXCLUDED.reconciliation_state,
            imported_summary = EXCLUDED.imported_summary, source_metadata = EXCLUDED.source_metadata
        RETURNING * INTO roster;
        END IF;
        IF nullif(data->>'status','') IS NOT NULL THEN
            attendance_date := (data->>'session_date')::date;
            PERFORM mark_faculty_attendance(p_actor, p_tenant, item.section_id, attendance_date,
                jsonb_build_object(roster.roster_id::text, data->>'status'), NULL);
        END IF;
        count_rows := count_rows + 1;
    END LOOP;
    UPDATE faculty_attendance_imports SET status = 'IMPORTED', summary = summary || jsonb_build_object('imported', count_rows, 'rejected', 0)
      WHERE import_id = p_import_id;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.commit', 'faculty_attendance_imports', p_import_id::text,
        jsonb_build_object('imported_rows', count_rows), 'success');
    RETURN jsonb_build_object('import_id', p_import_id, 'imported_rows', count_rows, 'status', 'IMPORTED');
END; $$;

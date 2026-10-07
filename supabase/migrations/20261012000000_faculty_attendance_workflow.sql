-- Extend Phase 10 in place. No attendance/student/assignment table is replaced.
ALTER TABLE public.faculty_attendance_rosters
    ADD COLUMN reconciliation_state text NOT NULL DEFAULT 'NONE'
        CHECK (reconciliation_state IN ('NONE','PENDING','LINKED','CONFLICT')),
    ADD COLUMN reconciliation_errors jsonb NOT NULL DEFAULT '[]';
ALTER TABLE public.faculty_attendance_import_rows ADD COLUMN warnings jsonb NOT NULL DEFAULT '[]';

-- A polymorphic trigger must branch before referring to table-specific fields.
-- SQL boolean AND does not guarantee short-circuit record-field resolution.
CREATE OR REPLACE FUNCTION public.faculty_attendance_context_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE tenant uuid; offering uuid; semester uuid; year_id uuid;
BEGIN
    SELECT d.institution_id, sec.course_offering_id, co.semester_id, co.academic_year_id
    INTO tenant, offering, semester, year_id FROM sections sec
    JOIN course_offerings co ON co.course_offering_id=sec.course_offering_id
    JOIN courses c ON c.course_id=co.course_id JOIN departments d ON d.department_id=c.department_id
    WHERE sec.section_id=NEW.section_id;
    IF tenant IS NULL OR NEW.institution_id IS DISTINCT FROM tenant OR NEW.course_offering_id IS DISTINCT FROM offering THEN
        RAISE EXCEPTION 'Attendance academic scope mismatch' USING ERRCODE='23514';
    END IF;
    IF TG_TABLE_NAME='faculty_attendance_rosters' THEN
        IF NEW.semester_id IS DISTINCT FROM semester THEN RAISE EXCEPTION 'Roster semester mismatch' USING ERRCODE='23514'; END IF;
        IF NEW.linked_student_id IS NOT NULL THEN
            IF NOT EXISTS(SELECT 1 FROM students WHERE student_id=NEW.linked_student_id AND institution_id=tenant) THEN
                RAISE EXCEPTION 'Linked student tenant mismatch' USING ERRCODE='23514';
            END IF;
        END IF;
    ELSIF TG_TABLE_NAME='faculty_attendance_imports' THEN
        IF NEW.semester_id IS DISTINCT FROM semester OR NEW.academic_year_id IS DISTINCT FROM year_id THEN
            RAISE EXCEPTION 'Import academic scope mismatch' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END; $$;

-- Make existing registered attendance visible in the Faculty roster using
-- actual student identity. Historical records stay in student_attendance.
INSERT INTO public.faculty_attendance_rosters(institution_id,section_id,course_offering_id,semester_id,
    register_number,university_roll_number,student_name,email,created_by,linked_student_id,roster_status,reconciliation_state)
SELECT DISTINCT ON (a.section_id,s.student_id) a.institution_id,a.section_id,sec.course_offering_id,co.semester_id,
    coalesce(s.register_number,s.student_number),s.university_roll_number,btrim(u.first_name||' '||u.last_name),s.email,u.id,
    CASE WHEN s.approval_status='approved' THEN s.student_id ELSE NULL END,
    CASE WHEN s.approval_status<>'approved' THEN 'PENDING_APPROVAL' WHEN s.is_active AND s.status='active' THEN 'ACTIVE' ELSE 'INACTIVE' END,
    CASE WHEN s.approval_status='approved' THEN 'LINKED' ELSE 'PENDING' END
FROM public.student_attendance a JOIN public.students s ON s.student_id=a.student_id AND s.institution_id=a.institution_id
JOIN public.users u ON u.id=s.user_id JOIN public.sections sec ON sec.section_id=a.section_id
JOIN public.course_offerings co ON co.course_offering_id=sec.course_offering_id
WHERE nullif(btrim(u.first_name||' '||u.last_name),'') IS NOT NULL
ORDER BY a.section_id,s.student_id,a.date
ON CONFLICT DO NOTHING;

-- Defense in depth for transactional writes. The application continues using
-- the centralized academic resolver. Responsibilities never grant mutation.
CREATE FUNCTION public.assert_faculty_attendance_mutation(p_actor uuid, p_tenant uuid, p_section uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE ctx jsonb;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || p_tenant::text, 0));
    SELECT jsonb_build_object('course_offering_id', co.course_offering_id,
        'semester_id', co.semester_id, 'academic_year_id', co.academic_year_id,
        'program_id', co.program_id) INTO ctx
    FROM users u JOIN user_roles ur ON ur.user_id = u.id
    JOIN roles role ON role.id = ur.role_id
    JOIN role_permissions rp ON rp.role_id = role.id
    JOIN permissions perm ON perm.permission_id = rp.permission_id
    JOIN institutions i ON i.institution_id = p_tenant
    JOIN faculty_section_assignments a ON a.faculty_user_id = u.id AND a.institution_id = p_tenant
    JOIN sections sec ON sec.section_id = a.section_id
    JOIN course_offerings co ON co.course_offering_id = sec.course_offering_id
    JOIN courses c ON c.course_id = co.course_id
    JOIN departments d ON d.department_id = c.department_id
    JOIN programs prog ON prog.program_id = co.program_id
    JOIN departments pd ON pd.department_id = prog.department_id
    JOIN semesters sem ON sem.semester_id = co.semester_id
    JOIN academic_years yr ON yr.academic_year_id = co.academic_year_id
    WHERE u.id = p_actor AND u.status = 'active' AND role.name = 'faculty' AND role.is_active
      AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
      AND perm.is_active AND perm.code IN ('attendance.manage', 'attendance.*', '*')
      AND i.status = 'active' AND i.is_active AND sec.section_id = p_section
      AND sec.is_active AND co.is_active AND c.is_active AND d.is_active
      AND prog.is_active AND pd.is_active AND sem.is_active AND yr.is_active
      AND d.institution_id = p_tenant AND pd.institution_id = p_tenant AND yr.institution_id = p_tenant
      AND sem.academic_year_id = co.academic_year_id
      AND a.is_active AND a.revoked_at IS NULL AND a.start_at <= clock_timestamp()
      AND (a.end_at IS NULL OR clock_timestamp() < a.end_at)
    LIMIT 1 FOR SHARE OF u, ur, role, rp, perm, i, a, sec, co, c, d, prog, pd, sem, yr;
    IF ctx IS NULL THEN RAISE EXCEPTION 'Teaching mutation denied' USING ERRCODE = '42501'; END IF;
    RETURN ctx;
END; $$;

CREATE FUNCTION public.faculty_attendance_identity(p_tenant uuid, p_register text, p_roll text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE ids uuid[]; s public.students;
BEGIN
    SELECT array_agg(student_id) INTO ids FROM students
    WHERE institution_id = p_tenant AND
      ((nullif(btrim(p_register), '') IS NOT NULL AND register_number = btrim(p_register)) OR
       (nullif(btrim(p_roll), '') IS NOT NULL AND university_roll_number = btrim(p_roll)));
    IF cardinality(ids) > 1 THEN RETURN '{"conflict":true}'::jsonb; END IF;
    IF ids IS NULL THEN RETURN '{"conflict":false}'::jsonb; END IF;
    SELECT * INTO s FROM students WHERE student_id = ids[1] FOR SHARE;
    IF (nullif(btrim(p_register),'') IS NOT NULL AND nullif(s.register_number,'') IS NOT NULL AND s.register_number <> btrim(p_register))
       OR (nullif(btrim(p_roll),'') IS NOT NULL AND nullif(s.university_roll_number,'') IS NOT NULL AND s.university_roll_number <> btrim(p_roll)) THEN
        RETURN '{"conflict":true}'::jsonb;
    END IF;
    RETURN jsonb_build_object('conflict', false, 'student_id', s.student_id,
        'approval_status', s.approval_status, 'is_active', s.is_active, 'status', s.status,
        'program_id', s.program_id, 'academic_year_id', s.academic_year_id);
END; $$;

CREATE FUNCTION public.mark_faculty_attendance(p_actor uuid, p_tenant uuid, p_section_id uuid,
    p_session_date date, p_attendance jsonb, p_notes text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE ctx jsonb; session public.faculty_attendance_sessions; entry record;
    roster public.faculty_attendance_rosters; corrected boolean; linked_count integer := 0;
BEGIN
    ctx := assert_faculty_attendance_mutation(p_actor, p_tenant, p_section_id);
    IF jsonb_typeof(p_attendance) <> 'object' OR p_attendance = '{}'::jsonb
        OR (SELECT count(*) FROM jsonb_object_keys(p_attendance)) > 500 OR length(p_notes) > 2000 THEN
        RAISE EXCEPTION 'Invalid attendance payload' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO session FROM faculty_attendance_sessions
      WHERE section_id = p_section_id AND session_date = p_session_date FOR UPDATE;
    corrected := session.session_id IS NOT NULL;
    IF corrected AND session.conducted_by <> p_actor THEN
        RAISE EXCEPTION 'Session belongs to another teacher' USING ERRCODE = '42501';
    END IF;
    IF NOT corrected THEN
        INSERT INTO faculty_attendance_sessions(institution_id, section_id, course_offering_id, session_date, conducted_by)
        VALUES(p_tenant, p_section_id, (ctx->>'course_offering_id')::uuid, p_session_date, p_actor) RETURNING * INTO session;
        INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
        VALUES(p_actor, p_tenant, 'attendance.session.create', 'faculty_attendance_sessions', session.session_id::text,
            jsonb_build_object('section_id', p_section_id, 'date', p_session_date), 'success');
    END IF;
    FOR entry IN SELECT * FROM jsonb_each_text(p_attendance) LOOP
        IF entry.value NOT IN ('present','absent','late','excused') THEN
            RAISE EXCEPTION 'Invalid attendance status' USING ERRCODE = '23514';
        END IF;
        SELECT * INTO roster FROM faculty_attendance_rosters WHERE roster_id = entry.key::uuid
          AND institution_id = p_tenant AND section_id = p_section_id FOR UPDATE;
        IF roster.roster_id IS NULL THEN RAISE EXCEPTION 'Student scope denied' USING ERRCODE = '42501'; END IF;
        INSERT INTO faculty_attendance_records(session_id, roster_id, status, notes)
        VALUES(session.session_id, roster.roster_id, entry.value, p_notes)
        ON CONFLICT(session_id, roster_id) DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes;
        IF roster.linked_student_id IS NOT NULL AND roster.reconciliation_state <> 'CONFLICT' THEN
            INSERT INTO student_attendance(student_id, institution_id, section_id, academic_year_id, semester_id, date, status, notes)
            VALUES(roster.linked_student_id, p_tenant, p_section_id, (ctx->>'academic_year_id')::uuid,
                (ctx->>'semester_id')::uuid, p_session_date, entry.value, p_notes)
            ON CONFLICT(student_id, section_id, date) DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes;
            linked_count := linked_count + 1;
        END IF;
    END LOOP;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, CASE WHEN corrected THEN 'attendance.session.correct' ELSE 'attendance.session.mark' END,
        'faculty_attendance_sessions', session.session_id::text,
        jsonb_build_object('record_count', (SELECT count(*) FROM jsonb_object_keys(p_attendance))), 'success');
    RETURN jsonb_build_object('session_id', session.session_id, 'record_count', (SELECT count(*) FROM jsonb_object_keys(p_attendance)),
        'updated_existing_student_records', linked_count, 'corrected', corrected);
END; $$;

CREATE FUNCTION public.review_faculty_attendance_import(p_actor uuid, p_tenant uuid, p_import_id uuid,
    p_summary jsonb, p_rows jsonb, p_expected_updated_at timestamptz)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE item public.faculty_attendance_imports; row jsonb;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || p_tenant::text, 0));
    SELECT * INTO item FROM faculty_attendance_imports WHERE import_id = p_import_id AND institution_id = p_tenant FOR UPDATE;
    IF item.import_id IS NULL OR item.uploaded_by <> p_actor THEN RAISE EXCEPTION 'Import scope denied' USING ERRCODE = '42501'; END IF;
    PERFORM assert_faculty_attendance_mutation(p_actor, p_tenant, item.section_id);
    IF item.updated_at IS DISTINCT FROM p_expected_updated_at OR item.status = 'IMPORTED' THEN
        RAISE EXCEPTION 'Import changed' USING ERRCODE = '40001';
    END IF;
    DELETE FROM faculty_attendance_import_rows WHERE import_id = p_import_id;
    FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        INSERT INTO faculty_attendance_import_rows(import_id, row_number, raw_data, normalized_data, validation_status, errors, warnings)
        VALUES(p_import_id, (row->>'row_number')::integer, row->'raw_data', row->'normalized_data',
            row->>'validation_status', row->'errors', coalesce(row->'warnings','[]'::jsonb));
    END LOOP;
    UPDATE faculty_attendance_imports SET summary = p_summary, status = 'REVIEWED' WHERE import_id = p_import_id;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.review', 'faculty_attendance_imports', p_import_id::text, p_summary, 'success');
    RETURN jsonb_build_object('import_id', p_import_id);
END; $$;

CREATE FUNCTION public.stage_faculty_attendance_import(p_actor uuid, p_tenant uuid, p_section_id uuid,
    p_semester_id uuid, p_filename text, p_file_type text, p_strategy text, p_ai_confirmed boolean,
    p_summary jsonb, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE ctx jsonb; id uuid; row jsonb;
BEGIN
    ctx := assert_faculty_attendance_mutation(p_actor, p_tenant, p_section_id);
    IF ctx->>'semester_id' <> p_semester_id::text THEN
        RAISE EXCEPTION 'Semester scope mismatch' USING ERRCODE = '23514';
    END IF;
    INSERT INTO faculty_attendance_imports(institution_id, section_id, course_offering_id, academic_year_id,
        semester_id, uploaded_by, original_filename, file_type, processing_strategy,
        ai_confirmation_required, ai_confirmed_at, status, summary)
    VALUES(p_tenant, p_section_id, (ctx->>'course_offering_id')::uuid, (ctx->>'academic_year_id')::uuid,
        p_semester_id, p_actor, p_filename, p_file_type, p_strategy, p_strategy = 'OCR_AI',
        CASE WHEN p_ai_confirmed THEN now() ELSE NULL END, 'VALIDATED', p_summary) RETURNING import_id INTO id;
    FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        INSERT INTO faculty_attendance_import_rows(import_id, row_number, raw_data, normalized_data, validation_status, errors, warnings)
        VALUES(id, (row->>'row_number')::integer, row->'raw_data', row->'normalized_data', row->>'validation_status', row->'errors', coalesce(row->'warnings','[]'::jsonb));
    END LOOP;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.create', 'faculty_attendance_imports', id::text, p_summary, 'success');
    RETURN jsonb_build_object('import_id', id);
END; $$;

CREATE FUNCTION public.commit_faculty_attendance_import(p_actor uuid, p_tenant uuid, p_import_id uuid,
    p_expected_updated_at timestamptz, p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE item public.faculty_attendance_imports; ctx jsonb; row jsonb; data jsonb; identity jsonb;
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
        identity := faculty_attendance_identity(p_tenant, data->>'register_number', data->>'university_roll_number');
        IF (identity->>'conflict')::boolean OR
            (identity->>'program_id' IS NOT NULL AND identity->>'program_id' <> ctx->>'program_id') OR
            (identity->>'academic_year_id' IS NOT NULL AND identity->>'academic_year_id' <> ctx->>'academic_year_id') THEN
            RAISE EXCEPTION 'Identity conflict' USING ERRCODE = '23514';
        END IF;
        student := CASE WHEN identity->>'approval_status' = 'approved' THEN (identity->>'student_id')::uuid ELSE NULL END;
        SELECT * INTO old FROM faculty_attendance_rosters WHERE institution_id = p_tenant AND section_id = item.section_id
            AND register_number = data->>'register_number' FOR UPDATE;
        IF old.roster_id IS NOT NULL AND ((old.linked_student_id IS NOT NULL AND old.linked_student_id IS DISTINCT FROM student)
            OR (nullif(old.university_roll_number,'') IS NOT NULL AND nullif(data->>'university_roll_number','') IS NOT NULL
                AND old.university_roll_number <> data->>'university_roll_number')) THEN
            RAISE EXCEPTION 'Existing roster identity conflict' USING ERRCODE = '23514';
        END IF;
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

-- Registration uses the existing students insert/approval lifecycle. Exact
-- identifiers must agree; pending accounts never become linked identities.
CREATE OR REPLACE FUNCTION public.reconcile_faculty_attendance_roster_student()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE r public.faculty_attendance_rosters; identity jsonb; student uuid;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || NEW.institution_id::text, 0));
    FOR r IN SELECT * FROM faculty_attendance_rosters WHERE institution_id = NEW.institution_id
        AND (linked_student_id = NEW.student_id OR register_number = NEW.register_number OR
             (NEW.university_roll_number IS NOT NULL AND university_roll_number = NEW.university_roll_number)) FOR UPDATE LOOP
        identity := faculty_attendance_identity(NEW.institution_id, r.register_number, r.university_roll_number);
        student := (identity->>'student_id')::uuid;
        IF (identity->>'conflict')::boolean OR (r.linked_student_id IS NOT NULL AND r.linked_student_id IS DISTINCT FROM student) THEN
            UPDATE faculty_attendance_rosters SET reconciliation_state = 'CONFLICT',
                reconciliation_errors = '["Conflicting or ambiguous student identifiers require administrator reconciliation"]'::jsonb
              WHERE roster_id = r.roster_id;
        ELSIF student = NEW.student_id THEN
            IF NEW.approval_status = 'approved' THEN
                UPDATE faculty_attendance_rosters SET linked_student_id = student, reconciliation_state = 'LINKED', reconciliation_errors = '[]',
                    roster_status = CASE WHEN NEW.is_active AND NEW.status = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END WHERE roster_id = r.roster_id;
                INSERT INTO student_attendance(student_id, institution_id, section_id, academic_year_id, semester_id, date, status, notes)
                SELECT student, NEW.institution_id, s.section_id, co.academic_year_id, co.semester_id, s.session_date, rec.status, rec.notes
                FROM faculty_attendance_records rec JOIN faculty_attendance_sessions s ON s.session_id = rec.session_id
                JOIN course_offerings co ON co.course_offering_id = s.course_offering_id WHERE rec.roster_id = r.roster_id
                ON CONFLICT(student_id, section_id, date) DO NOTHING;
            ELSE
                UPDATE faculty_attendance_rosters SET reconciliation_state = 'PENDING', roster_status = 'PENDING_APPROVAL'
                  WHERE roster_id = r.roster_id AND linked_student_id IS NULL;
            END IF;
        END IF;
        INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
        VALUES(NEW.user_id, NEW.institution_id, 'attendance.identity.reconcile', 'faculty_attendance_rosters', r.roster_id::text,
            jsonb_build_object('conflict', (identity->>'conflict')::boolean, 'approval_status', NEW.approval_status), 'success');
    END LOOP;
    RETURN NEW;
END; $$;
DROP TRIGGER trg_reconcile_faculty_attendance_roster ON public.students;
CREATE TRIGGER trg_reconcile_faculty_attendance_roster AFTER INSERT OR UPDATE OF
    register_number, university_roll_number, approval_status, status, is_active ON public.students
    FOR EACH ROW EXECUTE FUNCTION public.reconcile_faculty_attendance_roster_student();

-- Quarantine inconsistent links inherited from the former OR-based resolver.
-- Preserve every ID/link/history row; never guess which person owns a conflict.
UPDATE public.faculty_attendance_rosters r
SET reconciliation_state = 'CONFLICT',
    reconciliation_errors = '["Existing identity link requires administrator reconciliation"]'::jsonb
FROM (SELECT roster_id, public.faculty_attendance_identity(institution_id,register_number,university_roll_number) AS identity
      FROM public.faculty_attendance_rosters) checked
WHERE r.roster_id=checked.roster_id AND ((checked.identity->>'conflict')::boolean OR
    (r.linked_student_id IS NOT NULL AND r.linked_student_id IS DISTINCT FROM (checked.identity->>'student_id')::uuid));

-- Sync approved identities already registered before this extension. The
-- existing registration trigger applies the same conflict and history guards.
UPDATE public.students s SET approval_status=s.approval_status
WHERE s.approval_status='approved' AND EXISTS(SELECT 1 FROM public.faculty_attendance_rosters r
    WHERE r.institution_id=s.institution_id AND (r.linked_student_id=s.student_id OR r.register_number=s.register_number OR
        (s.university_roll_number IS NOT NULL AND r.university_roll_number=s.university_roll_number)));

REVOKE ALL ON FUNCTION public.assert_faculty_attendance_mutation(uuid,uuid,uuid),
    public.faculty_attendance_identity(uuid,text,text),
    public.mark_faculty_attendance(uuid,uuid,uuid,date,jsonb,text),
    public.stage_faculty_attendance_import(uuid,uuid,uuid,uuid,text,text,text,boolean,jsonb,jsonb),
    public.review_faculty_attendance_import(uuid,uuid,uuid,jsonb,jsonb,timestamptz),
    public.commit_faculty_attendance_import(uuid,uuid,uuid,timestamptz,jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.mark_faculty_attendance(uuid,uuid,uuid,date,jsonb,text),
    public.stage_faculty_attendance_import(uuid,uuid,uuid,uuid,text,text,text,boolean,jsonb,jsonb),
    public.review_faculty_attendance_import(uuid,uuid,uuid,jsonb,jsonb,timestamptz),
    public.commit_faculty_attendance_import(uuid,uuid,uuid,timestamptz,jsonb) TO service_role;

-- Transaction-local planning. The builder owns BEGIN and the final outcome.
SET LOCAL lock_timeout = '8s';
SET LOCAL statement_timeout = '90s';
CREATE TEMP TABLE reset_target(institution_id uuid PRIMARY KEY, code text NOT NULL) ON COMMIT DROP;
-- TARGET is replaced by the builder, never inferred from application defaults.
INSERT INTO reset_target VALUES ('__INSTITUTION_ID__', '__INSTITUTION_CODE__');
DO $$
BEGIN
    IF current_user <> 'postgres' OR NOT EXISTS (
        SELECT 1 FROM public.institutions i JOIN reset_target t USING(institution_id)
        WHERE i.code = t.code AND i.status = 'active'
    ) THEN RAISE EXCEPTION 'Pinned institution and database-owner access required'; END IF;
END;
$$;
-- Block writes briefly while recording a consistent preservation proof.
DO $$
DECLARE item record;
BEGIN
    FOR item IN SELECT c.oid::regclass AS relation FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public','auth','supabase_migrations') AND c.relkind = 'r'
          AND has_table_privilege(current_user,c.oid,'SELECT')
        ORDER BY c.oid LOOP
        IF item.relation::text LIKE 'auth.%' THEN
            -- Managed Auth metadata is not application-owned. Read locks plus
            -- before/after fingerprints refuse concurrent account changes.
            EXECUTE format('LOCK TABLE %s IN ACCESS SHARE MODE', item.relation);
        ELSE
            EXECUTE format('LOCK TABLE %s IN SHARE ROW EXCLUSIVE MODE', item.relation);
        END IF;
    END LOOP;
END;
$$;
CREATE TEMP TABLE reset_tables(name text PRIMARY KEY, relation oid NOT NULL, position integer NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE reset_rows(relation oid, tuple_id tid, row_digest text NOT NULL,
    PRIMARY KEY(relation, tuple_id)) ON COMMIT DROP;
-- Parent-first order also defines a child-first DELETE order.
DO $$
DECLARE names text[] := ARRAY[
    'departments','academic_years','programs','courses','semesters','academic_batches',
    'program_courses','course_offerings','sections','student_registrations',
    'student_registration_invitations','faculty_section_assignments','faculty_responsibilities',
    'faculty_attendance_rosters','faculty_attendance_sessions','faculty_tests',
    'faculty_attendance_records','faculty_attendance_imports','faculty_attendance_import_rows',
    'student_attendance','student_results','student_result_items','test_results',
    'academic_curricula','academic_curriculum_subjects','academic_subject_packages',
    'academic_package_subjects','academic_classes','academic_class_packages',
    'academic_class_subjects','academic_class_responsibilities','academic_class_placements',
    'academic_package_assignments','academic_package_revisions','academic_subject_participation',
    'academic_package_requests'];
    owners jsonb := '{
        "programs":["department_id","departments","department_id"],
        "courses":["department_id","departments","department_id"],
        "semesters":["academic_year_id","academic_years","academic_year_id"],
        "program_courses":["program_id","programs","program_id"],
        "course_offerings":["program_id","programs","program_id"],
        "sections":["course_offering_id","course_offerings","course_offering_id"],
        "faculty_attendance_records":["session_id","faculty_attendance_sessions","session_id"],
        "faculty_attendance_import_rows":["import_id","faculty_attendance_imports","import_id"],
        "student_result_items":["student_result_id","student_results","student_result_id"],
        "academic_curriculum_subjects":["curriculum_id","academic_curricula","curriculum_id"],
        "academic_subject_packages":["curriculum_id","academic_curricula","curriculum_id"],
        "academic_package_subjects":["package_id","academic_subject_packages","package_id"],
        "academic_class_packages":["class_id","academic_classes","class_id"],
        "academic_class_subjects":["class_id","academic_classes","class_id"],
        "academic_class_responsibilities":["class_id","academic_classes","class_id"],
        "academic_class_placements":["class_id","academic_classes","class_id"],
        "academic_package_assignments":["placement_id","academic_class_placements","placement_id"],
        "academic_package_revisions":["assignment_id","academic_package_assignments","assignment_id"],
        "academic_subject_participation":["placement_id","academic_class_placements","placement_id"],
        "academic_package_requests":["assignment_id","academic_package_assignments","assignment_id"]}';
    name text; rel oid; owner jsonb; predicate text; position integer := 0;
BEGIN
    FOREACH name IN ARRAY names LOOP
        position := position + 1;
        rel := to_regclass(format('public.%I', name));
        IF rel IS NULL THEN
            RAISE EXCEPTION 'Required academic table missing: %; install reviewed academic schema first', name;
        END IF;
        INSERT INTO reset_tables VALUES (name, rel, position);
        owner := owners->name;
        IF owner IS NULL THEN
            predicate := 't.institution_id = (SELECT institution_id FROM reset_target)';
            IF name = 'faculty_responsibilities' THEN
                predicate := predicate || ' AND (t.scope_type <> ''institution'' OR
                    t.department_id IS NOT NULL OR t.program_id IS NOT NULL OR t.semester_id IS NOT NULL
                    OR t.academic_year_id IS NOT NULL OR t.section_id IS NOT NULL OR t.course_id IS NOT NULL)';
            END IF;
        ELSE
            predicate := format('EXISTS (SELECT 1 FROM public.%I p JOIN reset_rows r
                ON r.relation = %L::regclass AND r.tuple_id = p.ctid WHERE t.%I = p.%I)',
                owner->>1, 'public.' || (owner->>1), owner->>0, owner->>2);
        END IF;
        EXECUTE format('INSERT INTO reset_rows SELECT %s, t.ctid, md5(to_jsonb(t)::text)
            FROM public.%I t WHERE %s', rel, name, predicate);
    END LOOP;
END;
$$;

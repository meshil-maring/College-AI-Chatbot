-- Read-only catalog evidence for the Quest academic-only reset.
-- No account, authentication, token, email, or academic row data is exported.
WITH target_names(name) AS (VALUES
    ('departments'), ('programs'), ('courses'), ('academic_years'), ('semesters'),
    ('program_courses'), ('course_offerings'), ('sections'), ('academic_batches'),
    ('student_registrations'), ('student_registration_invitations'),
    ('student_results'), ('student_result_items'), ('test_results'), ('student_attendance'),
    ('faculty_section_assignments'), ('faculty_responsibilities'), ('faculty_tests'),
    ('faculty_attendance_rosters'), ('faculty_attendance_sessions'), ('faculty_attendance_records'),
    ('faculty_attendance_imports'), ('faculty_attendance_import_rows'),
    ('academic_curricula'), ('academic_curriculum_subjects'), ('academic_subject_packages'),
    ('academic_package_subjects'), ('academic_classes'), ('academic_class_packages'),
    ('academic_class_subjects'), ('academic_class_responsibilities'),
    ('academic_class_placements'), ('academic_package_assignments'),
    ('academic_package_revisions'), ('academic_subject_participation'), ('academic_package_requests')
), targets AS (
    SELECT c.oid, c.relname, c.relkind, c.relowner
    FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname IN (SELECT name FROM target_names)
), dependencies AS (
    SELECT con.oid, con.conname, con.conrelid, con.confrelid,
        con.confdeltype, con.condeferrable, con.condeferred, con.convalidated
    FROM pg_catalog.pg_constraint con
    WHERE con.contype = 'f' AND (con.conrelid IN (SELECT oid FROM targets)
        OR con.confrelid IN (SELECT oid FROM targets))
)
SELECT jsonb_build_object(
    'database', current_database(), 'database_role', current_user,
    'target', jsonb_build_object('institution_id', '93d79749-0164-4cbf-b378-5fdff295d7af',
        'institution_code', 'QUEST123'),
    'tables', (SELECT coalesce(jsonb_agg(jsonb_build_object(
        'name', t.relname, 'kind', t.relkind, 'owner', pg_get_userbyid(t.relowner),
        'columns', (SELECT jsonb_agg(jsonb_build_object('name', a.attname,
            'type', pg_catalog.format_type(a.atttypid, a.atttypmod), 'not_null', a.attnotnull)
            ORDER BY a.attnum) FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped))
        ORDER BY t.relname), '[]'::jsonb) FROM targets t),
    'foreign_keys', (SELECT coalesce(jsonb_agg(jsonb_build_object(
        'constraint', d.conname, 'from', d.conrelid::regclass::text,
        'to', d.confrelid::regclass::text, 'definition', pg_get_constraintdef(d.oid),
        'delete_action', d.confdeltype, 'deferrable', d.condeferrable,
        'validated', d.convalidated) ORDER BY d.conrelid::regclass::text, d.conname),
        '[]'::jsonb) FROM dependencies d),
    'triggers', (SELECT coalesce(jsonb_agg(jsonb_build_object(
        'table', c.relname, 'name', tr.tgname, 'enabled', tr.tgenabled,
        'function', tr.tgfoid::regprocedure::text, 'definition', pg_get_triggerdef(tr.oid))
        ORDER BY c.relname, tr.tgname), '[]'::jsonb)
        FROM pg_catalog.pg_trigger tr JOIN pg_catalog.pg_class c ON c.oid = tr.tgrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND NOT tr.tgisinternal
          AND (c.oid IN (SELECT oid FROM targets) OR c.relname IN
              ('students', 'faculty', 'faculty_profiles', 'staff', 'staff_profiles', 'user_roles', 'user_permission_grants'))),
    'profile_academic_columns', (SELECT coalesce(jsonb_agg(jsonb_build_object(
        'table', c.relname, 'column', a.attname, 'not_null', a.attnotnull,
        'type', pg_catalog.format_type(a.atttypid, a.atttypmod)) ORDER BY c.relname, a.attname), '[]'::jsonb)
        FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname IN
            ('users', 'students', 'faculty', 'faculty_profiles', 'staff', 'staff_profiles')
          AND a.attnum > 0 AND NOT a.attisdropped
          AND a.attname IN ('department_id','program_id','academic_year_id','semester_id','section_id','batch_id')),
    'schema_version', jsonb_build_object(
        'curricula_present', to_regclass('public.academic_curricula') IS NOT NULL,
        'classes_present', to_regclass('public.academic_classes') IS NOT NULL,
        'registration_delivery_present', to_regclass('public.student_registration_invitations') IS NOT NULL),
    'scope_columns', (SELECT coalesce(jsonb_agg(jsonb_build_object(
        'table', c.relname, 'column', a.attname, 'not_null', a.attnotnull)
        ORDER BY c.relname, a.attname), '[]'::jsonb)
        FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname IN ('user_roles','user_permission_grants','faculty_responsibilities')
          AND a.attnum > 0 AND NOT a.attisdropped
          AND a.attname IN ('scope_type','scope_id','institution_id','department_id','program_id','section_id'))
) AS academic_reset_catalog;

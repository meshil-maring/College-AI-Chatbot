-- Preserve the superseded setup and every row; never guess dated semester data.
-- A pre-existing archive signals an unexpected baseline and aborts atomically.
SET LOCAL lock_timeout = '10s';
DO $$
DECLARE tables oid[];
BEGIN
    tables := ARRAY[
        'public.departments'::regclass, 'public.programs'::regclass,
        'public.academic_years'::regclass, 'public.study_semesters'::regclass,
        'public.subjects'::regclass, 'public.class_sections'::regclass,
        'public.section_subject_assignments'::regclass
    ];
    IF EXISTS(SELECT 1 FROM pg_catalog.pg_constraint
              WHERE contype='f' AND confrelid=ANY(tables) AND NOT conrelid=ANY(tables))
       OR EXISTS(SELECT 1 FROM pg_catalog.pg_depend d
           JOIN pg_catalog.pg_rewrite r ON d.classid='pg_catalog.pg_rewrite'::regclass AND r.oid=d.objid
           JOIN pg_catalog.pg_class c ON c.oid=r.ev_class
           WHERE d.refobjid=ANY(tables) AND c.relkind IN ('v','m')) THEN
        RAISE EXCEPTION 'Unexpected dependent relation; review before replacing Academic Setup';
    END IF;
END;
$$;
CREATE SCHEMA academic_setup_previous AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA academic_setup_previous FROM PUBLIC, anon, authenticated, service_role;
DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'departments', 'programs', 'academic_years', 'study_semesters',
        'subjects', 'class_sections', 'section_subject_assignments'
    ] LOOP
        EXECUTE format('LOCK TABLE public.%I IN ACCESS EXCLUSIVE MODE', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', relation_name);
        EXECUTE format('ALTER TABLE public.%I SET SCHEMA academic_setup_previous', relation_name);
    END LOOP;
END;
$$;
REVOKE ALL ON FUNCTION public.manage_academic_foundation(uuid, uuid, text, uuid, jsonb),
    public.manage_academic_structure(uuid, uuid, text, uuid, jsonb),
    public.manage_academic_sections(uuid, uuid, text, uuid, jsonb)
    FROM PUBLIC, anon, authenticated, service_role;

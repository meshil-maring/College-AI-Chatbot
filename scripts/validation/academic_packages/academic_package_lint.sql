CREATE EXTENSION IF NOT EXISTS plpgsql_check WITH SCHEMA extensions;
DO $$
DECLARE routine record; diagnostic record; findings integer := 0; checked integer := 0;
BEGIN
    FOR routine IN
        SELECT p.oid, p.oid::regprocedure AS name FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_catalog.pg_language l ON l.oid = p.prolang
        WHERE n.nspname = 'public' AND l.lanname = 'plpgsql'
          AND p.prorettype <> 'trigger'::regtype
          AND (p.proname LIKE 'academic_package_%' OR p.proname IN
            ('academic_legacy_section_authorize', 'assign_student_subject',
             'delete_academic_roster', 'phase81_manage_staff_permission_grants',
             'commit_faculty_attendance_import', 'save_faculty_test_marks',
             'transition_faculty_test'))
    LOOP
        checked := checked + 1;
        FOR diagnostic IN SELECT * FROM extensions.plpgsql_check_function_tb(
            routine.oid, fatal_errors := false)
        LOOP
            IF diagnostic.level IN ('error', 'fatal error') THEN
                RAISE NOTICE '% line %: % %; query: %', routine.name,
                    diagnostic.lineno, diagnostic.sqlstate, diagnostic.message, diagnostic.query;
                findings := findings + 1;
            END IF;
        END LOOP;
    END LOOP;
    FOR routine IN
        SELECT DISTINCT p.oid, p.oid::regprocedure AS name, t.tgrelid
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_catalog.pg_trigger t ON t.tgfoid = p.oid
        WHERE n.nspname = 'public' AND (p.proname LIKE 'academic_package_%'
            OR p.proname = 'test_results_tenant_guard')
          AND NOT t.tgisinternal
    LOOP
        checked := checked + 1;
        FOR diagnostic IN SELECT * FROM extensions.plpgsql_check_function_tb(
            routine.oid, routine.tgrelid, fatal_errors := false)
        LOOP
            IF diagnostic.level IN ('error', 'fatal error') THEN
                RAISE NOTICE '% line %: % %; query: %', routine.name,
                    diagnostic.lineno, diagnostic.sqlstate, diagnostic.message, diagnostic.query;
                findings := findings + 1;
            END IF;
        END LOOP;
    END LOOP;
    IF findings <> 0 THEN RAISE EXCEPTION 'Package SQL lint: % errors', findings; END IF;
    RAISE NOTICE 'PASS: package SQL lint, % function/trigger contexts checked', checked;
END;
$$;

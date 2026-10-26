DO $$
BEGIN
    IF academic_setup_check.capture(true) IS DISTINCT FROM
        (SELECT value FROM academic_setup_check.snapshots WHERE name='rollback') THEN
        RAISE EXCEPTION 'Decommission failure did not restore legacy rows, schema, ACLs and routines';
    END IF;
    IF to_regclass('public.programs') IS NULL
        OR to_regprocedure('public.academic_package_command(uuid,uuid,text,jsonb)') IS NULL THEN
        RAISE EXCEPTION 'Legacy Academic Setup runtime was not restored';
    END IF;
END $$;

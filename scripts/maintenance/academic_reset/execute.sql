-- Only explicit history/delete guards are paused, while every affected table
-- is locked. No global trigger bypass, FK disabling, cascade, or TRUNCATE.
DO $$
DECLARE item record;
BEGIN
    FOR item IN SELECT * FROM reset_trigger_state WHERE
        (tgrelid = 'public.test_results'::regclass AND tgname = 'workflow_result_delete')
        OR (tgrelid = 'public.faculty_attendance_rosters'::regclass AND tgname = 'academic_package_roster_write_guard') LOOP
        IF item.tgenabled <> 'O' THEN RAISE EXCEPTION 'Unexpected history guard state: %', item.tgname; END IF;
        EXECUTE format('ALTER TABLE %s DISABLE TRIGGER %I', item.tgrelid::regclass, item.tgname);
    END LOOP;
END;
$$;
SET LOCAL collegeai.test_write = 'rpc';
DO $$
DECLARE item record; removed bigint;
BEGIN
    -- Subject history is deleted before rosters and academic masters.
    FOR item IN SELECT * FROM reset_tables ORDER BY position DESC LOOP
        EXECUTE format('DELETE FROM %s t USING reset_rows r WHERE r.relation = %s AND r.tuple_id = t.ctid',
            item.relation::regclass, item.relation);
        GET DIAGNOSTICS removed = ROW_COUNT;
        IF removed <> (SELECT deleted_rows FROM reset_counts WHERE name = item.name) THEN
            RAISE EXCEPTION 'Unexpected deletion count for %', item.name;
        END IF;
    END LOOP;
    FOR item IN SELECT * FROM reset_trigger_state WHERE
        (tgrelid = 'public.test_results'::regclass AND tgname = 'workflow_result_delete')
        OR (tgrelid = 'public.faculty_attendance_rosters'::regclass AND tgname = 'academic_package_roster_write_guard') LOOP
        EXECUTE format('ALTER TABLE %s ENABLE TRIGGER %I', item.tgrelid::regclass, item.tgname);
    END LOOP;
    IF EXISTS ((SELECT * FROM reset_before EXCEPT SELECT * FROM pg_temp.reset_fingerprints())
        UNION ALL (SELECT * FROM pg_temp.reset_fingerprints() EXCEPT SELECT * FROM reset_before)) THEN
        RAISE EXCEPTION 'Account, role, audit, unrelated module, or other-tenant preservation check failed';
    END IF;
    IF EXISTS (SELECT 1 FROM reset_trigger_state s FULL JOIN (
        SELECT tgrelid,tgname,tgenabled,pg_get_triggerdef(oid) definition FROM pg_trigger
        WHERE NOT tgisinternal AND tgrelid IN (SELECT relation FROM reset_tables)
    ) actual USING(tgrelid,tgname) WHERE (s.tgenabled,s.definition) IS DISTINCT FROM (actual.tgenabled,actual.definition)) THEN
        RAISE EXCEPTION 'Trigger restoration verification failed';
    END IF;
END;
$$;
SELECT jsonb_build_object('institution_id',(SELECT institution_id FROM reset_target),
    'institution_code',(SELECT code FROM reset_target),
    'plan_digest',(SELECT digest FROM reset_plan),
    'deleted_rows',(SELECT sum(deleted_rows) FROM reset_counts),
    'academic_tables',(SELECT jsonb_object_agg(name,deleted_rows) FROM reset_counts),
    'preserved_tables',(SELECT count(*) FROM reset_before),
    'preservation_verified',true,'trigger_restoration_verified',true) AS academic_reset_result;
DROP FUNCTION pg_temp.reset_fingerprints();

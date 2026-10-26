BEGIN;
CREATE FUNCTION academic_setup_check.race_wait(kind text, peer text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE deadline timestamptz:=clock_timestamp()+interval '15 seconds'; ready boolean; w jsonb; key bigint;
BEGIN
    SELECT value INTO STRICT w FROM academic_setup_check.race_worlds WHERE name='a';
    key:=hashtextextended('academic-foundations:'||(w->>'tenant'),0);
    LOOP
        PERFORM pg_stat_clear_snapshot();
        IF kind='holder' THEN
            SELECT EXISTS (SELECT 1 FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
                WHERE a.application_name=peer AND l.locktype='advisory' AND l.granted
                AND l.classid=((key>>32)&4294967295)::oid AND l.objid=(key&4294967295)::oid
                AND l.objsubid=1) INTO ready;
        ELSIF kind='blocked' THEN
            SELECT EXISTS (SELECT 1 FROM pg_stat_activity a
                WHERE a.application_name=peer AND pg_backend_pid()=ANY(pg_blocking_pids(a.pid))) INTO ready;
        ELSIF kind='independent' THEN
            SELECT EXISTS (SELECT 1 FROM public.departments WHERE code='RACE_TENANT'
                AND institution_id=(SELECT (value->>'tenant')::uuid
                    FROM academic_setup_check.race_worlds WHERE name='b')) INTO ready;
        ELSE RAISE EXCEPTION 'Unknown synchronization condition';
        END IF;
        -- A late successful observation is still a timeout.
        IF clock_timestamp()>=deadline THEN RAISE EXCEPTION 'Race synchronization deadline exceeded'; END IF;
        IF ready THEN RETURN; END IF;
        PERFORM pg_sleep(0.01);
    END LOOP;
END $$;
REVOKE ALL ON FUNCTION academic_setup_check.race_wait(text,text) FROM PUBLIC,anon,authenticated,service_role;
COMMIT;

-- Original retained catalog projection, installed before any decommission call.
CREATE FUNCTION academic_setup_check.retained_inventory() RETURNS jsonb
LANGUAGE plpgsql SET search_path='' AS $$
DECLARE inventory jsonb:=academic_setup_check.catalog_inventory(); item record; projected_columns jsonb;
BEGIN
    FOR item IN SELECT key FROM jsonb_each(inventory->'tables')
        WHERE key IN (SELECT 'public.'||name FROM academic_setup_check.retired_tables) LOOP
        inventory:=inventory #- ARRAY['tables',item.key];
    END LOOP;
    IF inventory->'tables' ? 'public.students' THEN
        SELECT COALESCE(jsonb_agg(v ORDER BY position),'[]'::jsonb) INTO projected_columns
        FROM jsonb_array_elements(inventory->'tables'->'public.students'->'columns')
            WITH ORDINALITY AS attributes(v,position)
        WHERE v->>'name' NOT IN ('program_id','academic_year_id');
        inventory:=jsonb_set(inventory,ARRAY['tables','public.students','columns'],projected_columns);
    END IF;
    FOR item IN SELECT p.oid::regprocedure::text AS signature,p.proname
        FROM pg_proc p WHERE p.pronamespace='public'::regnamespace LOOP
        IF item.proname IN (SELECT name FROM academic_setup_check.retired_functions) THEN
            inventory:=inventory #- ARRAY['routines',item.signature];
        ELSIF item.signature='public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)' THEN
            -- Only this sanctioned body replacement is ignored; retain its
            -- owner, ACL, argument/return, SECURITY DEFINER and configuration.
            inventory:=jsonb_set(inventory,ARRAY['routines',item.signature,'definition'],'null'::jsonb);
            inventory:=jsonb_set(inventory,ARRAY['routines',item.signature,'catalog','prosrc'],'null'::jsonb);
        END IF;
    END LOOP;
    FOR item IN SELECT key,value FROM jsonb_each(inventory->'sequences') LOOP
        IF EXISTS (SELECT 1 FROM jsonb_array_elements(item.value->'owned_by') dependency
            WHERE dependency->>'schema'='public'
                AND dependency->>'table' IN (SELECT name FROM academic_setup_check.retired_tables)) THEN
            inventory:=inventory #- ARRAY['sequences',item.key];
        END IF;
    END LOOP;
    RETURN inventory;
END $$;
CREATE FUNCTION academic_setup_check.assert_retained_state(original jsonb, current_state jsonb) RETURNS void
LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
    IF jsonb_typeof(original->'inventory'->'tables') IS DISTINCT FROM 'object'
        OR jsonb_typeof(original->'inventory'->'routines') IS DISTINCT FROM 'object'
        OR jsonb_typeof(original->'inventory'->'sequences') IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'Original retained baseline missing' USING ERRCODE='P4202';
    END IF;
    IF current_state IS DISTINCT FROM original THEN
        RAISE EXCEPTION 'Retained pre-decommission state changed' USING ERRCODE='P4202';
    END IF;
END $$;
CREATE FUNCTION academic_setup_check.verify_decommission_retained() RETURNS void
LANGUAGE plpgsql SET search_path='' AS $$
DECLARE original jsonb;
BEGIN
    SELECT value INTO STRICT original FROM academic_setup_check.snapshots WHERE name='retained';
    PERFORM academic_setup_check.assert_retained_state(original,academic_setup_check.capture(false));
END $$;
CREATE FUNCTION academic_setup_check.expect_retained_change(command text) RETURNS void
LANGUAGE plpgsql SET search_path='' AS $$
DECLARE baseline jsonb:=academic_setup_check.capture(true); detected boolean;
    original jsonb:=(SELECT value FROM academic_setup_check.snapshots WHERE name='retained');
BEGIN
    BEGIN
        EXECUTE command;
        -- Rebase only the later academic snapshots, deliberately. They must
        -- never substitute for the immutable original retained baseline.
        UPDATE academic_setup_check.snapshots
        SET value=academic_setup_check.capture(name='post_decommission_catalog')
        WHERE name IN ('post_decommission','post_decommission_catalog');
        detected:=false;
        BEGIN
            PERFORM academic_setup_check.verify_decommission_retained();
        EXCEPTION WHEN SQLSTATE 'P4202' THEN
            IF SQLERRM<>'Retained pre-decommission state changed' THEN RAISE; END IF;
            detected:=true;
        END;
        IF NOT detected THEN RAISE EXCEPTION 'Retained catalog alteration was accepted'; END IF;
        RAISE EXCEPTION USING ERRCODE='P4099';
    EXCEPTION WHEN SQLSTATE 'P4099' THEN NULL;
    END;
    IF academic_setup_check.capture(true) IS DISTINCT FROM baseline
        OR (SELECT value FROM academic_setup_check.snapshots WHERE name='retained') IS DISTINCT FROM original THEN
        RAISE EXCEPTION 'Retained control failed to restore state';
    END IF;
END $$;

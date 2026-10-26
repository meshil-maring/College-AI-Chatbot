-- Synthetic rows stay inside the disposable database; never print snapshots.
BEGIN;
CREATE SCHEMA academic_setup_check;
CREATE TABLE academic_setup_check.retired_tables(name text PRIMARY KEY);
INSERT INTO academic_setup_check.retired_tables VALUES __RETIRED_TABLE_VALUES__;
CREATE TABLE academic_setup_check.retired_functions(name text PRIMARY KEY);
INSERT INTO academic_setup_check.retired_functions VALUES __RETIRED_FUNCTION_VALUES__;
CREATE TABLE academic_setup_check.snapshots(name text PRIMARY KEY,value jsonb NOT NULL);
__CATALOG_CAPTURE_SQL__
__RETAINED_CAPTURE_SQL__
__RETAINED_FIXTURES_SQL__
CREATE FUNCTION academic_setup_check.capture(full_state boolean) RETURNS jsonb
LANGUAGE plpgsql SET search_path='' AS $$
DECLARE item record; rows jsonb; columns jsonb; constraints jsonb; objects jsonb;
    tables jsonb := '{}'; routines jsonb; projection text; predicate text;
    academic_pattern text := '^(academic\.|attendance\.|results\.|faculty\.assignments\.|departments\.|courses\.|subjects\.|semesters\.|academic_years\.|programs\.|sections\.|section_subjects\.)';
BEGIN
    FOR item IN SELECT c.oid,n.nspname,c.relname,c.relrowsecurity,c.relforcerowsecurity,
        c.relacl,c.relowner
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind='r' AND (n.nspname='public' OR (n.nspname='auth' AND c.relname='users'))
        AND (full_state OR NOT (n.nspname='public' AND c.relname IN
            (SELECT name FROM academic_setup_check.retired_tables)))
        ORDER BY n.nspname,c.relname LOOP
        projection := CASE WHEN NOT full_state AND item.nspname='public' AND item.relname='students'
            THEN 'to_jsonb(t)-ARRAY[''program_id'',''academic_year_id'']' ELSE 'to_jsonb(t)' END;
        predicate := '';
        IF NOT full_state AND item.nspname='public'
            AND item.relname IN ('permissions','role_permissions','user_permission_grants') THEN
            predicate := format('WHERE permission_id NOT IN (SELECT permission_id FROM public.permissions WHERE code ~ %L)',academic_pattern);
        END IF;
        EXECUTE format('SELECT COALESCE(jsonb_agg(row ORDER BY row::text),''[]''::jsonb) FROM '
            || '(SELECT %s AS row FROM %I.%I t %s) source',projection,item.nspname,item.relname,predicate) INTO rows;
        SELECT COALESCE(jsonb_agg(jsonb_build_object('name',a.attname,
            'type',pg_catalog.format_type(a.atttypid,a.atttypmod),'notnull',a.attnotnull,
            'default',pg_catalog.pg_get_expr(d.adbin,d.adrelid),'acl',a.attacl::text)
            ORDER BY a.attnum),'[]'::jsonb)
        INTO columns FROM pg_catalog.pg_attribute a
        LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
        WHERE a.attrelid=item.oid AND a.attnum>0 AND NOT a.attisdropped
        AND (full_state OR item.nspname<>'public' OR item.relname<>'students'
            OR a.attname NOT IN ('program_id','academic_year_id'));
        SELECT COALESCE(jsonb_agg(jsonb_build_object('name',con.conname,
            'definition',pg_catalog.pg_get_constraintdef(con.oid)) ORDER BY con.conname),'[]'::jsonb)
        INTO constraints FROM pg_catalog.pg_constraint con WHERE con.conrelid=item.oid
        AND (full_state OR con.contype<>'f' OR NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_class parent
            JOIN pg_catalog.pg_namespace ns ON ns.oid=parent.relnamespace
            JOIN academic_setup_check.retired_tables retired ON retired.name=parent.relname
            WHERE parent.oid=con.confrelid AND ns.nspname='public'));
        SELECT jsonb_build_object(
            'triggers',(SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'name',t.tgname,'enabled',t.tgenabled,'definition',pg_get_triggerdef(t.oid))
                ORDER BY t.tgname),'[]'::jsonb) FROM pg_trigger t
                WHERE t.tgrelid=item.oid
                -- New academic FKs add internal triggers on retained parents.
                -- The full snapshot includes these; the retained projection
                -- excludes only triggers owned by these sanctioned domain FKs.
                AND (full_state OR NOT t.tgisinternal OR NOT EXISTS (
                    SELECT 1 FROM pg_constraint con JOIN pg_class child ON child.oid=con.conrelid
                    WHERE con.oid=t.tgconstraint AND child.relnamespace='public'::regnamespace
                    AND child.relname IN ('departments','programs','academic_years','study_semesters',
                        'subjects','class_sections','section_subject_assignments')))
                AND (full_state OR NOT EXISTS (SELECT 1 FROM pg_constraint con
                    JOIN pg_class relation ON relation.oid IN (con.conrelid,con.confrelid)
                    JOIN academic_setup_check.retired_tables retired ON retired.name=relation.relname
                    WHERE con.oid=t.tgconstraint AND relation.relnamespace='public'::regnamespace))
                AND (full_state OR NOT EXISTS (SELECT 1 FROM pg_proc f
                    JOIN academic_setup_check.retired_functions r ON r.name=f.proname
                    WHERE f.oid=t.tgfoid AND f.pronamespace='public'::regnamespace))),
            'policies',(SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'name',p.polname,'command',p.polcmd,'permissive',p.polpermissive,
                'roles',(SELECT jsonb_agg(r ORDER BY r) FROM unnest(p.polroles) r),
                'using',pg_get_expr(p.polqual,p.polrelid),
                'check',pg_get_expr(p.polwithcheck,p.polrelid)) ORDER BY p.polname),'[]'::jsonb)
                FROM pg_policy p WHERE p.polrelid=item.oid),
            'indexes',(SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'name',c.relname,'definition',pg_get_indexdef(i.indexrelid),
                'valid',i.indisvalid,'ready',i.indisready,'clustered',i.indisclustered,
                'replica_identity',i.indisreplident,'owner',pg_get_userbyid(c.relowner))
                ORDER BY c.relname),'[]'::jsonb) FROM pg_index i
                JOIN pg_class c ON c.oid=i.indexrelid WHERE i.indrelid=item.oid)) INTO objects;
        -- Dropped student ancestry keys also remove their indexes, if any.
        IF NOT full_state AND item.nspname='public' AND item.relname='students' THEN
            objects := jsonb_set(objects,'{indexes}',COALESCE((SELECT jsonb_agg(v ORDER BY v->>'name')
                FROM jsonb_array_elements(objects->'indexes') v
                WHERE v->>'definition' !~ '\m(program_id|academic_year_id)\M'),'[]'::jsonb));
        END IF;
        tables := tables || jsonb_build_object(item.nspname||'.'||item.relname,
            jsonb_build_object('rows',rows,'columns',columns,'constraints',constraints,
                'rls',item.relrowsecurity,'force_rls',item.relforcerowsecurity,
                'owner',pg_get_userbyid(item.relowner),'acl',item.relacl::text,'objects',objects));
    END LOOP;
    SELECT COALESCE(jsonb_object_agg(p.oid::regprocedure::text,
        jsonb_build_object('definition',pg_catalog.pg_get_functiondef(p.oid),
            'owner',pg_get_userbyid(p.proowner),'acl',p.proacl::text)),'{}'::jsonb)
    INTO routines FROM pg_catalog.pg_proc p
    WHERE p.pronamespace='public'::regnamespace AND p.prokind='f'
        AND (full_state OR (p.proname NOT IN (SELECT name FROM academic_setup_check.retired_functions)
            AND p.proname<>'phase81_manage_staff_permission_grants'));
    RETURN jsonb_build_object('tables',tables,'routines',routines,
        'schemas',(SELECT jsonb_object_agg(nspname,jsonb_build_object(
            'owner',pg_get_userbyid(nspowner),'acl',nspacl::text))
            FROM pg_namespace WHERE nspname IN ('public','auth')),
        'default_acls',(SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'owner',pg_get_userbyid(defaclrole),'schema',defaclnamespace::regnamespace::text,
            'type',defaclobjtype,'acl',defaclacl::text) ORDER BY defaclrole,defaclnamespace,defaclobjtype),
            '[]'::jsonb) FROM pg_default_acl),
        'sequences',(SELECT COALESCE(jsonb_object_agg(n.nspname||'.'||c.relname,
            jsonb_build_object('owner',pg_get_userbyid(c.relowner),'acl',c.relacl::text,
                'type',format_type(s.seqtypid,NULL),'start',s.seqstart,'min',s.seqmin,
                'max',s.seqmax,'increment',s.seqincrement,'cache',s.seqcache,'cycle',s.seqcycle)),
            '{}'::jsonb) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_sequence s ON s.seqrelid=c.oid WHERE n.nspname IN ('public','auth')
            AND (full_state OR NOT EXISTS (SELECT 1 FROM pg_depend d
                JOIN pg_class parent ON parent.oid=d.refobjid
                JOIN academic_setup_check.retired_tables retired ON retired.name=parent.relname
                WHERE d.objid=c.oid AND parent.relnamespace='public'::regnamespace
                    AND d.classid='pg_class'::regclass AND d.refclassid='pg_class'::regclass
                    AND d.deptype IN ('a','i')))))
        || jsonb_build_object('inventory',CASE WHEN full_state THEN academic_setup_check.catalog_inventory()
            ELSE academic_setup_check.retained_inventory() END);
END $$;
INSERT INTO academic_setup_check.snapshots VALUES
    ('rollback',academic_setup_check.capture(true)),
    ('retained',academic_setup_check.capture(false)),
    ('post_decommission','{}'),
    ('post_decommission_catalog','{}');
CREATE FUNCTION academic_setup_check.assert_catalog_inventory(previous jsonb, current_state jsonb)
RETURNS void LANGUAGE plpgsql SET search_path='' AS $$
DECLARE group_name text; object_name text;
    approved jsonb:=jsonb_build_object(
        'tables',ARRAY['public.departments','public.programs','public.academic_years',
            'public.study_semesters','public.subjects','public.class_sections','public.section_subject_assignments'],
        'routines',ARRAY['public.assert_academic_foundation_actor(uuid,uuid,text)',
            'public.validate_academic_foundation()','public.validate_academic_structure()',
            'public.guard_academic_structure_parent()','public.validate_academic_sections()',
            'public.guard_academic_sections_parent()',
            'public.manage_academic_foundation(uuid,uuid,text,uuid,jsonb)',
            'public.manage_academic_structure(uuid,uuid,text,uuid,jsonb)',
            'public.manage_academic_sections(uuid,uuid,text,uuid,jsonb)'],
        'sequences','[]'::jsonb); -- Academic IDs are UUIDs; no new sequence is approved.
BEGIN
    FOREACH group_name IN ARRAY ARRAY['tables','routines','sequences'] LOOP
        IF jsonb_typeof(previous->group_name) IS DISTINCT FROM 'object'
            OR jsonb_typeof(current_state->group_name) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'Catalog inventory missing' USING ERRCODE='P4202';
        END IF;
        FOR object_name IN SELECT jsonb_object_keys(previous->group_name) LOOP
            IF NOT ((current_state->group_name) ? object_name) THEN
                RAISE EXCEPTION 'Retained catalog object removed' USING ERRCODE='P4202';
            END IF;
            IF current_state->group_name->object_name IS DISTINCT FROM previous->group_name->object_name THEN
                RAISE EXCEPTION 'Retained object changed during Academic Setup replay' USING ERRCODE='P4202';
            END IF;
        END LOOP;
        FOR object_name IN SELECT jsonb_object_keys(current_state->group_name) LOOP
            IF NOT ((previous->group_name) ? object_name)
                AND NOT ((approved->group_name) ? object_name) THEN
                RAISE EXCEPTION 'Unexpected added academic catalog object' USING ERRCODE='P4201';
            END IF;
        END LOOP;
    END LOOP;
END $$;
CREATE FUNCTION academic_setup_check.verify_post_academic() RETURNS void
LANGUAGE plpgsql SET search_path='' AS $$
DECLARE previous jsonb; inventory jsonb; catalog_state jsonb; current_state jsonb;
    previous_group jsonb; current_group jsonb; group_name text; item record;
BEGIN
    SELECT value INTO STRICT previous FROM academic_setup_check.snapshots WHERE name='post_decommission';
    SELECT value INTO STRICT inventory FROM academic_setup_check.snapshots WHERE name='post_decommission_catalog';
    IF previous='{}'::jsonb OR inventory='{}'::jsonb THEN
        RAISE EXCEPTION 'Post-decommission snapshot missing';
    END IF;
    -- Full inventory sees new objects even when the retained projection omits
    -- names formerly owned by the retired domain. Existing state stays projected.
    catalog_state:=academic_setup_check.capture(true);
    PERFORM academic_setup_check.assert_catalog_inventory(inventory->'inventory',catalog_state->'inventory');
    current_state := academic_setup_check.capture(false);
    IF to_regclass('academic_setup_check.race_expected_rows') IS NOT NULL THEN
        EXECUTE 'SELECT academic_setup_check.project_race_rows($1)' INTO current_state USING current_state;
    END IF;
    IF current_state->'schemas' IS DISTINCT FROM previous->'schemas'
        OR current_state->'default_acls' IS DISTINCT FROM previous->'default_acls' THEN
        RAISE EXCEPTION 'Retained namespace privileges changed';
    END IF;
    FOREACH group_name IN ARRAY ARRAY['tables','routines','sequences'] LOOP
        -- Only table state needs the sanctioned ancestry/permission projection.
        -- All pre-existing routines and sequences must remain unchanged in full.
        previous_group:=(CASE WHEN group_name='tables' THEN previous ELSE inventory END)->group_name;
        current_group:=(CASE WHEN group_name='tables' THEN current_state ELSE catalog_state END)->group_name;
        FOR item IN SELECT key,value FROM jsonb_each(previous_group) LOOP
            IF current_group->item.key IS DISTINCT FROM item.value THEN
                RAISE EXCEPTION 'Retained object changed during Academic Setup replay' USING ERRCODE='P4202';
            END IF;
        END LOOP;
    END LOOP;
END $$;
REVOKE ALL ON SCHEMA academic_setup_check FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON ALL TABLES IN SCHEMA academic_setup_check FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA academic_setup_check FROM PUBLIC,anon,authenticated,service_role;
COMMIT;

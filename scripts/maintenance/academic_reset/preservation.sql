-- Reject references from preserved rows, including cross-tenant corruption.
DO $$
DECLARE fk record; join_clause text; outside_rows bigint;
BEGIN
    FOR fk IN SELECT c.* FROM pg_constraint c WHERE c.contype = 'f'
        AND c.confrelid IN (SELECT relation FROM reset_tables) LOOP
        SELECT string_agg(format('child.%I = parent.%I', a.attname, b.attname), ' AND ' ORDER BY k.ordinality)
        INTO join_clause FROM unnest(fk.conkey, fk.confkey) WITH ORDINALITY k(child_key,parent_key,ordinality)
        JOIN pg_attribute a ON a.attrelid = fk.conrelid AND a.attnum = k.child_key
        JOIN pg_attribute b ON b.attrelid = fk.confrelid AND b.attnum = k.parent_key;
        -- Only these nullable academic profile fields are authorized exceptions.
        IF fk.conrelid = 'public.students'::regclass AND fk.conname IN
            ('students_program_id_fkey','students_academic_year_id_fkey') THEN
            EXECUTE format('SELECT count(*) FROM %s child JOIN %s parent ON %s
                JOIN reset_rows target ON target.relation = %s AND target.tuple_id = parent.ctid
                WHERE child.institution_id <> (SELECT institution_id FROM reset_target)',
                fk.conrelid::regclass, fk.confrelid::regclass, join_clause, fk.confrelid) INTO outside_rows;
        ELSE
            EXECUTE format('SELECT count(*) FROM %s child JOIN %s parent ON %s
                JOIN reset_rows target ON target.relation = %s AND target.tuple_id = parent.ctid
                WHERE NOT EXISTS (SELECT 1 FROM reset_rows r WHERE r.relation = %s AND r.tuple_id = child.ctid)',
                fk.conrelid::regclass, fk.confrelid::regclass, join_clause, fk.confrelid, fk.conrelid) INTO outside_rows;
        END IF;
        IF outside_rows > 0 THEN RAISE EXCEPTION 'Preserved dependency blocks reset: % (% rows)', fk.conname, outside_rows; END IF;
    END LOOP;
END;
$$;
CREATE FUNCTION pg_temp.reset_fingerprints() RETURNS TABLE(relation text, row_count bigint, digest text)
LANGUAGE plpgsql AS $$
DECLARE item record; representation text;
BEGIN
    FOR item IN SELECT c.oid, c.oid::regclass AS rel, n.nspname, c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public','auth','supabase_migrations') AND c.relkind = 'r'
          AND has_table_privilege(current_user,c.oid,'SELECT') ORDER BY c.oid LOOP
        representation := 'to_jsonb(t)';
        IF item.nspname = 'public' AND item.relname = 'students' THEN
            representation := 'CASE WHEN t.institution_id = (SELECT institution_id FROM reset_target)
                THEN to_jsonb(t) - ARRAY[''program_id'',''academic_year_id'',''updated_at''] ELSE to_jsonb(t) END';
        END IF;
        RETURN QUERY EXECUTE format('SELECT %L::text, count(*), md5(coalesce(string_agg(h, '''' ORDER BY h), ''''))
            FROM (SELECT md5((%s)::text) h FROM %s t WHERE NOT EXISTS
                (SELECT 1 FROM reset_rows r WHERE r.relation = %s AND r.tuple_id = t.ctid)) hashes',
            item.rel::text, representation, item.rel, item.oid);
    END LOOP;
END;
$$;
CREATE TEMP TABLE reset_before ON COMMIT DROP AS SELECT * FROM pg_temp.reset_fingerprints();
CREATE TEMP TABLE reset_trigger_state ON COMMIT DROP AS
    SELECT tgrelid, tgname, tgenabled, pg_get_triggerdef(oid) definition
    FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN (SELECT relation FROM reset_tables);
CREATE TEMP TABLE reset_counts ON COMMIT DROP AS
    SELECT t.name, t.position, count(r.tuple_id) AS deleted_rows FROM reset_tables t
    LEFT JOIN reset_rows r ON r.relation = t.relation GROUP BY t.name,t.position;
CREATE TEMP TABLE reset_plan ON COMMIT DROP AS
    SELECT md5(coalesce(string_agg(t.name || r.row_digest, '' ORDER BY t.name,r.row_digest), '')) AS digest
    FROM reset_rows r JOIN reset_tables t ON t.relation = r.relation;

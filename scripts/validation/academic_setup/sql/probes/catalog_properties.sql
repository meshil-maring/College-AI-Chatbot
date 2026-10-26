-- Same-name DDL controls against the original pre-decommission baseline.
SELECT academic_setup_check.expect_retained_change(command) FROM (VALUES
    ('CREATE RULE academic_preserved_rule AS ON UPDATE TO public.academic_preserved_table DO ALSO NOTIFY academic_fixture'),
    ('ALTER TABLE public.academic_preserved_table REPLICA IDENTITY FULL'),
    ('ALTER TABLE public.academic_preserved_table CLUSTER ON academic_preserved_note'),
    ('ALTER MATERIALIZED VIEW public.academic_preserved_materialized CLUSTER ON academic_preserved_materialized_id'),
    ('ALTER FOREIGN TABLE public.academic_preserved_foreign ALTER COLUMN id OPTIONS (SET probe ''two'')'),
    ('ALTER SERVER academic_preserved_server VERSION ''two'''),
    -- Server TYPE has no ALTER form in PostgreSQL 17. Recreate the handlerless
    -- server and its fixture table under their same names, without any I/O.
    ('DO $alter$ BEGIN DROP FOREIGN TABLE public.academic_preserved_foreign; '
        'DROP SERVER academic_preserved_server; '
        'CREATE SERVER academic_preserved_server TYPE ''other'' VERSION ''one'' FOREIGN DATA WRAPPER academic_preserved_fdw; '
        'GRANT USAGE ON FOREIGN SERVER academic_preserved_server TO academic_preserved_owner; '
        'CREATE FOREIGN TABLE public.academic_preserved_foreign(id integer OPTIONS (probe ''one'')) '
        'SERVER academic_preserved_server OPTIONS (probe ''one''); '
        'REVOKE ALL ON TABLE public.academic_preserved_foreign FROM PUBLIC,anon; END $alter$'),
    ('ALTER SEQUENCE public.academic_preserved_sequence OWNED BY public.academic_preserved_table.id'),
    ('ALTER SEQUENCE public.academic_preserved_sequence SET UNLOGGED')
) changes(command);
DO $$
DECLARE relation_name text; flag text; original jsonb; changed jsonb; detected boolean;
BEGIN
    -- No supported ALTER INDEX sets indisvalid/indisready directly. Deliberately
    -- failed concurrent builds cannot run inside this rollback-only transaction.
    -- Perturb fixture metadata, never system catalogs, to test the comparator.
    original:=academic_setup_check.catalog_inventory();
    FOREACH relation_name IN ARRAY ARRAY['public.academic_preserved_materialized','public.academic_preserved_partition'] LOOP
        FOREACH flag IN ARRAY ARRAY['valid','ready','clustered'] LOOP
            IF jsonb_array_length(original->'tables'->relation_name->'indexes')<>1 THEN
                RAISE EXCEPTION 'Index metadata control requires one fixture index';
            END IF;
            IF jsonb_typeof(original->'tables'->relation_name->'indexes'->0->flag) IS DISTINCT FROM 'boolean' THEN
                RAISE EXCEPTION 'Index control flag missing or malformed';
            END IF;
            changed:=jsonb_set(original,ARRAY['tables',relation_name,'indexes','0',flag],
                to_jsonb(NOT (original->'tables'->relation_name->'indexes'->0->>flag)::boolean));
            detected:=false;
            BEGIN
                PERFORM academic_setup_check.assert_catalog_inventory(original,changed);
            EXCEPTION WHEN SQLSTATE 'P4202' THEN
                IF SQLERRM<>'Retained object changed during Academic Setup replay' THEN RAISE; END IF;
                detected:=true;
            END;
            IF NOT detected THEN RAISE EXCEPTION 'Index metadata change accepted'; END IF;
        END LOOP;
    END LOOP;
    original:=academic_setup_check.capture(false);
    FOREACH flag IN ARRAY ARRAY['valid','ready','clustered'] LOOP
        IF jsonb_array_length(original->'tables'->'public.academic_preserved_table'->'objects'->'indexes')<1 THEN
            RAISE EXCEPTION 'Ordinary-table index metadata control requires a fixture index';
        END IF;
        IF jsonb_typeof(original->'tables'->'public.academic_preserved_table'->'objects'->'indexes'->0->flag)
            IS DISTINCT FROM 'boolean' THEN
            RAISE EXCEPTION 'Ordinary-table index control flag missing or malformed';
        END IF;
        changed:=jsonb_set(original,ARRAY['tables','public.academic_preserved_table','objects','indexes','0',flag],
            to_jsonb(NOT (original->'tables'->'public.academic_preserved_table'->'objects'->'indexes'->0->>flag)::boolean));
        detected:=false;
        BEGIN
            PERFORM academic_setup_check.assert_retained_state(original,changed);
        EXCEPTION WHEN SQLSTATE 'P4202' THEN
            IF SQLERRM<>'Retained pre-decommission state changed' THEN RAISE; END IF;
            detected:=true;
        END;
        IF NOT detected THEN RAISE EXCEPTION 'Ordinary-table index metadata change accepted'; END IF;
    END LOOP;
END $$;

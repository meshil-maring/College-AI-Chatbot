-- Prepared same-name controls for every claimed relation/routine kind.
-- Foreign metadata uses a handlerless server: no endpoint, user mapping or query.
BEGIN;
SELECT academic_setup_check.verify_post_academic();
CREATE ROLE academic_retention_owner NOLOGIN NOINHERIT;
GRANT USAGE,CREATE ON SCHEMA public TO academic_retention_owner;
CREATE VIEW public.academic_retained_view AS SELECT 1 AS id;
CREATE MATERIALIZED VIEW public.academic_retained_materialized AS SELECT 1 AS id WITH NO DATA;
CREATE TABLE public.academic_retained_partition(id integer) PARTITION BY RANGE(id);
CREATE FOREIGN DATA WRAPPER academic_retention_fdw NO HANDLER NO VALIDATOR;
CREATE SERVER academic_retention_server FOREIGN DATA WRAPPER academic_retention_fdw;
GRANT USAGE ON FOREIGN SERVER academic_retention_server TO academic_retention_owner;
CREATE FOREIGN TABLE public.academic_retained_foreign(id integer)
    SERVER academic_retention_server OPTIONS (probe 'one');
CREATE PROCEDURE public.academic_retained_procedure() LANGUAGE plpgsql AS $$ BEGIN NULL; END $$;
CREATE AGGREGATE public.academic_retained_aggregate(bigint) (SFUNC=pg_catalog.int8pl,STYPE=bigint);
CREATE FUNCTION public.academic_retained_window() RETURNS bigint LANGUAGE internal WINDOW AS 'window_row_number';
-- Normalize explicit fixture ACLs before measuring each grant mutation.
REVOKE ALL ON TABLE public.academic_retained_view,public.academic_retained_materialized,
    public.academic_retained_partition,public.academic_retained_foreign FROM PUBLIC,anon;
REVOKE ALL ON ROUTINE public.academic_retained_procedure(),
    public.academic_retained_aggregate(bigint),public.academic_retained_window() FROM PUBLIC,anon;
UPDATE academic_setup_check.snapshots
SET value=academic_setup_check.capture(name='post_decommission_catalog')
WHERE name IN ('post_decommission','post_decommission_catalog');
SELECT academic_setup_check.verify_post_academic();
DO $$
DECLARE command text; baseline jsonb:=academic_setup_check.capture(true);
BEGIN
    FOREACH command IN ARRAY ARRAY[
        'CREATE OR REPLACE VIEW public.academic_retained_view AS SELECT 2 AS id',
        'ALTER VIEW public.academic_retained_view OWNER TO academic_retention_owner',
        'GRANT SELECT ON TABLE public.academic_retained_view TO anon',
        'GRANT UPDATE(id) ON TABLE public.academic_retained_view TO anon',
        'DO $alter$ BEGIN DROP MATERIALIZED VIEW public.academic_retained_materialized; '
            'CREATE MATERIALIZED VIEW public.academic_retained_materialized AS SELECT 2 AS id WITH NO DATA; END $alter$',
        'ALTER MATERIALIZED VIEW public.academic_retained_materialized OWNER TO academic_retention_owner',
        'GRANT SELECT ON TABLE public.academic_retained_materialized TO anon',
        'DO $alter$ BEGIN DROP TABLE public.academic_retained_partition; '
            'CREATE TABLE public.academic_retained_partition(id integer) PARTITION BY LIST(id); END $alter$',
        'ALTER TABLE public.academic_retained_partition OWNER TO academic_retention_owner',
        'GRANT SELECT ON TABLE public.academic_retained_partition TO anon',
        'ALTER FOREIGN TABLE public.academic_retained_foreign OPTIONS (SET probe ''two'')',
        'ALTER FOREIGN TABLE public.academic_retained_foreign OWNER TO academic_retention_owner',
        'GRANT SELECT ON TABLE public.academic_retained_foreign TO anon',
        'CREATE OR REPLACE PROCEDURE public.academic_retained_procedure() LANGUAGE plpgsql AS ''BEGIN PERFORM 1; END''',
        'ALTER PROCEDURE public.academic_retained_procedure() OWNER TO academic_retention_owner',
        'GRANT EXECUTE ON PROCEDURE public.academic_retained_procedure() TO anon',
        'DO $alter$ BEGIN DROP AGGREGATE public.academic_retained_aggregate(bigint); '
            'CREATE AGGREGATE public.academic_retained_aggregate(bigint) (SFUNC=pg_catalog.int8mi,STYPE=bigint); END $alter$',
        'ALTER AGGREGATE public.academic_retained_aggregate(bigint) OWNER TO academic_retention_owner',
        'GRANT EXECUTE ON ROUTINE public.academic_retained_aggregate(bigint) TO anon',
        'CREATE OR REPLACE FUNCTION public.academic_retained_window() RETURNS bigint '
            'LANGUAGE internal WINDOW AS ''window_rank''',
        'ALTER FUNCTION public.academic_retained_window() OWNER TO academic_retention_owner',
        'GRANT EXECUTE ON FUNCTION public.academic_retained_window() TO anon'
    ] LOOP
        BEGIN
            EXECUTE command;
            PERFORM academic_setup_check.expect_error('SELECT academic_setup_check.verify_post_academic()',
                'P4202','Retained object changed during Academic Setup replay');
            RAISE EXCEPTION USING ERRCODE='P4099';
        EXCEPTION WHEN SQLSTATE 'P4099' THEN NULL;
        END;
        IF academic_setup_check.capture(true) IS DISTINCT FROM baseline THEN
            RAISE EXCEPTION 'Same-name alteration did not restore original catalog state';
        END IF;
    END LOOP;
    PERFORM academic_setup_check.verify_post_academic();
END $$;
ROLLBACK;

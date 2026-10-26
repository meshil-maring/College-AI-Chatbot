-- Injected after original decommission DDL/checks and before its final COMMIT.
-- The surrounding variant forces P4001 after these controls and rolls back.
SELECT academic_setup_check.verify_decommission_retained();
SELECT academic_setup_check.expect_retained_change(command) FROM (VALUES
    ('CREATE OR REPLACE VIEW public.academic_preserved_view AS SELECT 2 AS id'),
    ('ALTER VIEW public.academic_preserved_view OWNER TO academic_preserved_owner'),
    ('GRANT SELECT ON public.academic_preserved_view TO anon'),
    ('DO $alter$ BEGIN DROP MATERIALIZED VIEW public.academic_preserved_materialized; '
        'CREATE MATERIALIZED VIEW public.academic_preserved_materialized AS SELECT 2 AS id; '
        'CREATE INDEX academic_preserved_materialized_id ON public.academic_preserved_materialized(id); END $alter$'),
    ('ALTER MATERIALIZED VIEW public.academic_preserved_materialized OWNER TO academic_preserved_owner'),
    ('GRANT SELECT ON public.academic_preserved_materialized TO anon'),
    ('DO $alter$ BEGIN DROP TABLE public.academic_preserved_partition; '
        'CREATE TABLE public.academic_preserved_partition(id integer) PARTITION BY LIST(id); '
        'CREATE INDEX academic_preserved_partition_id ON public.academic_preserved_partition(id); END $alter$'),
    ('ALTER TABLE public.academic_preserved_partition OWNER TO academic_preserved_owner'),
    ('GRANT SELECT ON public.academic_preserved_partition TO anon'),
    ('ALTER FOREIGN TABLE public.academic_preserved_foreign OPTIONS (SET probe ''two'')'),
    ('ALTER FOREIGN TABLE public.academic_preserved_foreign OWNER TO academic_preserved_owner'),
    ('GRANT SELECT ON public.academic_preserved_foreign TO anon'),
    ('CREATE OR REPLACE PROCEDURE public.academic_preserved_procedure() LANGUAGE plpgsql AS ''BEGIN PERFORM 1; END'''),
    ('ALTER PROCEDURE public.academic_preserved_procedure() OWNER TO academic_preserved_owner'),
    ('GRANT EXECUTE ON PROCEDURE public.academic_preserved_procedure() TO anon'),
    ('DO $alter$ BEGIN DROP AGGREGATE public.academic_preserved_aggregate(bigint); '
        'CREATE AGGREGATE public.academic_preserved_aggregate(bigint) (SFUNC=pg_catalog.int8mi,STYPE=bigint); END $alter$'),
    ('ALTER AGGREGATE public.academic_preserved_aggregate(bigint) OWNER TO academic_preserved_owner'),
    ('GRANT EXECUTE ON ROUTINE public.academic_preserved_aggregate(bigint) TO anon'),
    ('CREATE OR REPLACE FUNCTION public.academic_preserved_window() RETURNS bigint LANGUAGE internal WINDOW AS ''window_rank'''),
    ('ALTER FUNCTION public.academic_preserved_window() OWNER TO academic_preserved_owner'),
    ('GRANT EXECUTE ON FUNCTION public.academic_preserved_window() TO anon'),
    ('ALTER TABLE public.academic_preserved_table SET (fillfactor=70)'),
    ('GRANT UPDATE(note) ON public.academic_preserved_table TO anon'),
    ('ALTER SEQUENCE public.academic_preserved_sequence OWNER TO academic_preserved_owner'),
    ('GRANT USAGE ON SEQUENCE public.academic_preserved_sequence TO anon')
) changes(command);
SELECT academic_setup_check.verify_decommission_retained();

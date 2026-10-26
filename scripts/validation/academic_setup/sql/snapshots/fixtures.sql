-- Synthetic preservation fixtures, captured before the first decommission call.
-- They remain until disposable-container destruction; foreign rows are never read.
CREATE ROLE academic_preserved_owner NOLOGIN NOINHERIT;
GRANT USAGE,CREATE ON SCHEMA public TO academic_preserved_owner;
CREATE TABLE public.academic_preserved_table(id integer PRIMARY KEY,note text);
CREATE INDEX academic_preserved_note ON public.academic_preserved_table(note);
CREATE VIEW public.academic_preserved_view AS SELECT 1 AS id;
CREATE MATERIALIZED VIEW public.academic_preserved_materialized AS SELECT 1 AS id;
CREATE INDEX academic_preserved_materialized_id ON public.academic_preserved_materialized(id);
CREATE TABLE public.academic_preserved_partition(id integer) PARTITION BY RANGE(id);
CREATE INDEX academic_preserved_partition_id ON public.academic_preserved_partition(id);
CREATE FOREIGN DATA WRAPPER academic_preserved_fdw NO HANDLER NO VALIDATOR;
CREATE SERVER academic_preserved_server TYPE 'synthetic' VERSION 'one'
    FOREIGN DATA WRAPPER academic_preserved_fdw;
GRANT USAGE ON FOREIGN SERVER academic_preserved_server TO academic_preserved_owner;
CREATE FOREIGN TABLE public.academic_preserved_foreign(id integer OPTIONS (probe 'one'))
    SERVER academic_preserved_server OPTIONS (probe 'one');
CREATE PROCEDURE public.academic_preserved_procedure() LANGUAGE plpgsql AS $$ BEGIN NULL; END $$;
CREATE AGGREGATE public.academic_preserved_aggregate(bigint) (SFUNC=pg_catalog.int8pl,STYPE=bigint);
CREATE FUNCTION public.academic_preserved_window() RETURNS bigint LANGUAGE internal WINDOW AS 'window_row_number';
CREATE SEQUENCE public.academic_preserved_sequence;
REVOKE ALL ON TABLE public.academic_preserved_table,public.academic_preserved_view,
    public.academic_preserved_materialized,public.academic_preserved_partition,
    public.academic_preserved_foreign FROM PUBLIC,anon;
REVOKE ALL ON ROUTINE public.academic_preserved_procedure(),
    public.academic_preserved_aggregate(bigint),public.academic_preserved_window() FROM PUBLIC,anon;
REVOKE ALL ON SEQUENCE public.academic_preserved_sequence FROM PUBLIC,anon;

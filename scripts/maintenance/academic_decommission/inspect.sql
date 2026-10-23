-- Read-only release evidence. Hashes/counts leave the database; row data does not.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
WITH targets AS (
    SELECT n.nspname,c.relname FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
    WHERE c.relkind='r' AND (n.nspname='public' OR (n.nspname='auth' AND c.relname='users'))
), fingerprints AS (
    SELECT nspname AS schema_name,relname AS table_name,
        ((xpath('/table/row/row_count/text()',evidence))[1])::text::bigint AS row_count,
        ((xpath('/table/row/fingerprint/text()',evidence))[1])::text AS fingerprint
    FROM targets CROSS JOIN LATERAL query_to_xml(format(
        'SELECT count(*) AS row_count,md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),''[]''::jsonb)::text) AS fingerprint FROM %I.%I t',
        nspname,relname),true,false,'') AS evidence
)
SELECT jsonb_build_object(
    'project_ref','rjnfmjcvkfotneswpygr','database',current_database(),'principal',current_user,
    'institutions',(SELECT COALESCE(jsonb_agg(jsonb_build_object('institution_id',institution_id,'code',code)
        ORDER BY institution_id),'[]'::jsonb) FROM public.institutions),
    'ledger',(SELECT COALESCE(jsonb_agg(version ORDER BY version),'[]'::jsonb) FROM supabase_migrations.schema_migrations),
    'ledger_columns',(SELECT jsonb_agg(jsonb_build_object('name',column_name,'type',data_type,'nullable',is_nullable,
        'default',column_default) ORDER BY ordinal_position) FROM information_schema.columns
        WHERE table_schema='supabase_migrations' AND table_name='schema_migrations'),
    'tables',(SELECT jsonb_agg(to_jsonb(fingerprints) ORDER BY schema_name,table_name) FROM fingerprints),
    'routines',(SELECT COALESCE(jsonb_agg(jsonb_build_object('identity',p.oid::regprocedure::text,
        'fingerprint',md5(pg_get_functiondef(p.oid))) ORDER BY p.oid::regprocedure::text),'[]'::jsonb)
        FROM pg_catalog.pg_proc p WHERE p.pronamespace='public'::regnamespace AND p.prokind='f')
) AS academic_decommission_inspection;
ROLLBACK;

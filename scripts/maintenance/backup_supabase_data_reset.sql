-- Sensitive data export: redirect the result to a private, Git-ignored file.
-- Do not paste the output into a chat, commit it, or publish it.
BEGIN ISOLATION LEVEL REPEATABLE READ;
SET LOCAL statement_timeout = '120s';
CREATE TEMP TABLE reset_backup (
    schema_name text,
    table_name text,
    row_count bigint,
    rows jsonb
) ON COMMIT DROP;

DO $backup$
DECLARE
    item record;
    contents jsonb;
BEGIN
    FOR item IN
        SELECT n.nspname, c.relname
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'auth')
          AND c.relkind IN ('r', 'p') AND NOT c.relispartition
          AND NOT EXISTS (
              SELECT 1 FROM pg_depend d
              WHERE d.classid = 'pg_class'::regclass
                AND d.objid = c.oid AND d.deptype = 'e'
          )
        ORDER BY n.nspname, c.relname
    LOOP
        EXECUTE format(
            'SELECT coalesce(jsonb_agg(to_jsonb(t)), ''[]''::jsonb) FROM %I.%I t',
            item.nspname, item.relname
        ) INTO contents;
        INSERT INTO reset_backup VALUES (
            item.nspname, item.relname, jsonb_array_length(contents), contents
        );
    END LOOP;
END;
$backup$;

SELECT jsonb_build_object(
    'exported_at', now(),
    'tables', (SELECT jsonb_agg(to_jsonb(b) ORDER BY b.schema_name, b.table_name) FROM reset_backup b)
) AS backup;
COMMIT;

-- The browser roles never read or write public tables directly; every access
-- goes through the backend with the service role. This matches live and guards
-- against new tables inheriting Supabase's default grants.
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;
SET LOCAL search_path = public, extensions;
SELECT plan(3);

SELECT is_empty(
    $$SELECT grantee || ' ' || privilege_type || ' ' || table_name
        FROM information_schema.role_table_grants
       WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')$$,
    'anon and authenticated have no privileges on public tables');

SELECT is_empty(
    $$SELECT c.relname FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname = 'public' AND c.relkind = 'S'
         AND (has_sequence_privilege('anon', c.oid, 'USAGE')
              OR has_sequence_privilege('authenticated', c.oid, 'USAGE'))$$,
    'anon and authenticated cannot use public sequences');

SELECT is_empty(
    $$SELECT defaclobjtype::text FROM pg_catalog.pg_default_acl d
        JOIN pg_catalog.pg_namespace n ON n.oid = d.defaclnamespace
       WHERE n.nspname = 'public' AND d.defaclobjtype IN ('r', 'S')
         AND d.defaclrole = 'postgres'::regrole
         AND (d.defaclacl::text LIKE '%anon=%' OR d.defaclacl::text LIKE '%authenticated=%')$$,
    'tables and sequences created by migrations do not grant the browser roles');

SELECT * FROM finish();
ROLLBACK;

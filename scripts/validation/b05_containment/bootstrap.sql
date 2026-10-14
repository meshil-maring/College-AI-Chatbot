-- PREPARATION ONLY. NOT EXECUTED. Apply only through a later authorized executor.
-- Fresh bare initdb cluster, postgres session, sole tmpfs and no TCP listener.
-- This local Auth/ledger shim proves no provider or gateway compatibility.
BEGIN;
DO $bootstrap_guard$
BEGIN
  IF current_user <> 'postgres' OR session_user <> 'postgres'
     OR current_database() <> 'postgres'
     OR current_setting('server_version_num')::integer <> 170006
     OR current_setting('data_directory') <> '/var/lib/postgresql/data'
     OR current_setting('listen_addresses') <> ''
     OR inet_server_addr() IS NOT NULL THEN
    RAISE EXCEPTION 'Fresh isolated PostgreSQL 17.6 Unix-socket target required';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname IN ('auth','extensions','supabase_migrations'))
     OR EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role'))
     OR EXISTS (SELECT 1 FROM pg_class WHERE relnamespace = 'public'::regnamespace) THEN
    RAISE EXCEPTION 'Bare initdb expected; bundled initialization or reused cluster prohibited';
  END IF;
END $bootstrap_guard$;
SET LOCAL search_path = pg_catalog;
SET LOCAL timezone = 'UTC';
CREATE ROLE anon NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;
CREATE ROLE authenticated NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT;
CREATE ROLE service_role NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS NOINHERIT;
-- No role memberships; postgres is the sole migration/object creator.
CREATE SCHEMA auth AUTHORIZATION postgres;
CREATE SCHEMA extensions AUTHORIZATION postgres;
CREATE SCHEMA supabase_migrations AUTHORIZATION postgres;
CREATE EXTENSION vector WITH SCHEMA extensions VERSION '0.8.0';
CREATE EXTENSION btree_gist WITH SCHEMA extensions VERSION '1.7';
GRANT USAGE ON SCHEMA auth, extensions TO anon, authenticated, service_role;
CREATE TABLE auth.users (
  id uuid PRIMARY KEY,
  email text NOT NULL UNIQUE,
  email_confirmed_at timestamptz,
  raw_user_meta_data jsonb NOT NULL DEFAULT '{}'::jsonb
);
REVOKE ALL ON auth.users FROM PUBLIC, anon, authenticated, service_role;
CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT COALESCE(NULLIF(current_setting('request.jwt.claims', true), '')::jsonb, '{}'::jsonb)
$$;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.sub', true), ''), auth.jwt()->>'sub')::uuid
$$;
CREATE FUNCTION auth.role() RETURNS text LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.role', true), ''), auth.jwt()->>'role')
$$;
CREATE FUNCTION auth.email() RETURNS text LANGUAGE sql STABLE SET search_path = '' AS $$
  SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.email', true), ''), auth.jwt()->>'email')
$$;
REVOKE ALL ON FUNCTION auth.jwt(), auth.uid(), auth.role(), auth.email() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth.jwt(), auth.uid(), auth.role(), auth.email() TO anon, authenticated, service_role;
CREATE TABLE supabase_migrations.schema_migrations (
  version text PRIMARY KEY CHECK (version ~ '^[0-9]{14}$'),
  statements text[] NOT NULL,
  name text NOT NULL
);
REVOKE ALL ON SCHEMA supabase_migrations FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON supabase_migrations.schema_migrations FROM PUBLIC, anon, authenticated, service_role;
COMMIT;

-- Synthetic local Auth shim only. No provider or hosted-service compatibility claim.
BEGIN;
DO $$
BEGIN
    IF current_user <> 'postgres' OR current_database() <> 'postgres'
        OR current_setting('server_version_num')::integer <> 170006
        OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspname IN ('auth','extensions'))
        OR EXISTS (SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace) THEN
        RAISE EXCEPTION 'Fresh PostgreSQL 17.6 cluster required';
    END IF;
END $$;
CREATE ROLE anon NOLOGIN NOINHERIT;
CREATE ROLE authenticated NOLOGIN NOINHERIT;
CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;
CREATE SCHEMA auth AUTHORIZATION postgres;
CREATE SCHEMA extensions AUTHORIZATION postgres;
CREATE EXTENSION vector WITH SCHEMA extensions VERSION '0.8.0';
CREATE EXTENSION btree_gist WITH SCHEMA extensions VERSION '1.7';
GRANT USAGE ON SCHEMA auth,extensions TO anon,authenticated,service_role;
CREATE TABLE auth.users (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE,
    email_confirmed_at timestamptz,
    raw_user_meta_data jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE SET search_path='' AS $$
    SELECT COALESCE(NULLIF(current_setting('request.jwt.claims',true),'')::jsonb,'{}'::jsonb)
$$;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE SET search_path='' AS $$
    SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.sub',true),''),auth.jwt()->>'sub')::uuid
$$;
CREATE FUNCTION auth.role() RETURNS text LANGUAGE sql STABLE SET search_path='' AS $$
    SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.role',true),''),auth.jwt()->>'role')
$$;
CREATE FUNCTION auth.email() RETURNS text LANGUAGE sql STABLE SET search_path='' AS $$
    SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.email',true),''),auth.jwt()->>'email')
$$;
REVOKE ALL ON auth.users FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION auth.jwt(),auth.uid(),auth.role(),auth.email() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth.jwt(),auth.uid(),auth.role(),auth.email() TO anon,authenticated,service_role;
COMMIT;

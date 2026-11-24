-- Make a fresh migration replay reproduce the live project's privileges.
--
-- A read-only schema comparison (2026-11-24) found that the live project grants
-- nothing on public tables or sequences to the browser roles, while a fresh
-- replay of the migrations inherits Supabase's default `GRANT ALL ... TO anon,
-- authenticated` on 27 early baseline tables and one later sequence. Local
-- tests and rehearsals were therefore more permissive than live. Every
-- statement here is already true on live, so applying it there changes nothing.
--
-- It also records two live-only objects: the role_permissions(permission_id)
-- index and ON UPDATE/DELETE CASCADE on users.auth_user_id. Both are created
-- only when missing.
BEGIN;

SET LOCAL lock_timeout = '10s';

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated;

CREATE INDEX IF NOT EXISTS role_permissions_permission_id_idx
    ON public.role_permissions USING btree (permission_id);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_constraint
        WHERE conname = 'users_auth_user_id_fkey'
          AND conrelid = 'public.users'::regclass
          AND (confdeltype <> 'c' OR confupdtype <> 'c')
    ) THEN
        ALTER TABLE public.users DROP CONSTRAINT users_auth_user_id_fkey;
        ALTER TABLE public.users ADD CONSTRAINT users_auth_user_id_fkey
            FOREIGN KEY (auth_user_id) REFERENCES auth.users(id)
            ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;
END;
$$;

COMMIT;

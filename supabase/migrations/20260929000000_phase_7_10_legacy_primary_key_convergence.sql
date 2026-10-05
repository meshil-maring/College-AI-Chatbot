-- Phase 7.10 -- converge deployments created from the legacy pre-7.9 schema.
--
-- Some existing projects were migrated before the reconstructed baseline was
-- corrected and therefore still expose public.users.user_id and
-- public.roles.role_id.  Current application code and every later migration
-- use the authoritative public.users.id / public.roles.id contract.
--
-- PostgreSQL column renames preserve the primary keys, data, indexes, and
-- dependent foreign keys.  The guarded blocks make this migration a no-op on
-- fresh databases that already have the authoritative column names.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'users'
           AND column_name = 'user_id'
    ) AND NOT EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'users'
           AND column_name = 'id'
    ) THEN
        ALTER TABLE public.users RENAME COLUMN user_id TO id;
    END IF;
END;
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'roles'
           AND column_name = 'role_id'
    ) AND NOT EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'roles'
           AND column_name = 'id'
    ) THEN
        ALTER TABLE public.roles RENAME COLUMN role_id TO id;
    END IF;
END;
$$;

-- Fail closed if either table has an unexpected third shape.  Later
-- migrations must never run against an ambiguous identity/RBAC contract.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'id'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'roles' AND column_name = 'id'
    ) THEN
        RAISE EXCEPTION 'Phase 7.10: users/roles primary-key convergence failed';
    END IF;
END;
$$;

-- Fresh baseline replay must converge before Phase 8 references permission_id.
-- Renaming retains all IDs and PostgreSQL updates dependent foreign keys.
-- Already-converged installations are unchanged.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'permissions' AND column_name = 'id') AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'permissions' AND column_name = 'permission_id') THEN
        ALTER TABLE public.permissions RENAME COLUMN id TO permission_id;
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'permissions' AND column_name = 'id') THEN
        RAISE EXCEPTION 'Ambiguous permission primary key columns require reconciliation';
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'permissions' AND column_name = 'permission_id') THEN
        RAISE EXCEPTION 'Permission primary key is unavailable';
    END IF;
END; $$;

-- Executable difference checks, reviewed offline here; every alteration rolls back.
BEGIN;
DO $$ BEGIN
    IF current_user<>'postgres' OR NOT (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) THEN
        RAISE EXCEPTION 'Snapshot controls require the isolated postgres owner';
    END IF;
END $$;
CREATE ROLE academic_snapshot_owner NOLOGIN NOINHERIT;
-- Ownership targets need CREATE on the schema; these fixture-only grants roll back.
GRANT USAGE,CREATE ON SCHEMA public TO academic_snapshot_owner;
CREATE TABLE public.academic_snapshot_probe(id integer, note text);
CREATE FUNCTION public.academic_snapshot_trigger() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$;
CREATE TRIGGER existing_probe BEFORE INSERT ON public.academic_snapshot_probe
    FOR EACH ROW EXECUTE FUNCTION public.academic_snapshot_trigger();
CREATE SEQUENCE public.academic_snapshot_sequence;
-- Normalize fixture ACLs so GRANT/REVOKE probes cannot silently become no-ops
-- under inherited default ACLs. No application object's grants are changed.
REVOKE ALL ON TABLE public.academic_snapshot_probe FROM PUBLIC,anon;
REVOKE ALL(note) ON TABLE public.academic_snapshot_probe FROM PUBLIC,anon;
REVOKE ALL ON SEQUENCE public.academic_snapshot_sequence FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.academic_snapshot_trigger() TO PUBLIC;
ALTER TABLE public.academic_snapshot_probe ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT has_schema_privilege('academic_snapshot_owner','public','CREATE')
        OR NOT pg_has_role(current_user,'academic_snapshot_owner','SET')
        OR EXISTS (SELECT 1 FROM pg_class WHERE oid IN ('public.academic_snapshot_probe'::regclass,
            'public.academic_snapshot_sequence'::regclass) AND relowner<>'postgres'::regrole)
        OR (SELECT proowner FROM pg_proc WHERE oid='public.academic_snapshot_trigger()'::regprocedure)
            IS DISTINCT FROM 'postgres'::regrole
        OR has_schema_privilege('academic_snapshot_owner','auth','CREATE')
        OR has_table_privilege('anon','public.academic_snapshot_probe','SELECT')
        OR has_any_column_privilege('anon','public.academic_snapshot_probe','UPDATE')
        OR has_sequence_privilege('anon','public.academic_snapshot_sequence','USAGE')
        OR NOT EXISTS (SELECT 1 FROM pg_proc p,
            LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) acl
            WHERE p.oid='public.academic_snapshot_trigger()'::regprocedure
                AND acl.grantee=0 AND acl.privilege_type='EXECUTE')
        OR EXISTS (SELECT 1 FROM pg_depend WHERE objid='public.academic_snapshot_sequence'::regclass
            AND classid='pg_class'::regclass AND refclassid='pg_class'::regclass AND deptype IN ('a','i')) THEN
        RAISE EXCEPTION 'Snapshot ownership or ACL mutation preconditions differ';
    END IF;
END $$;
CREATE FUNCTION academic_setup_check.expect_snapshot_change(command text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE before_state jsonb;
BEGIN
    before_state := academic_setup_check.capture(true);
    BEGIN
        EXECUTE command;
        IF academic_setup_check.capture(true) IS NOT DISTINCT FROM before_state THEN
            RAISE EXCEPTION 'Snapshot missed alteration: %',command;
        END IF;
        RAISE EXCEPTION USING ERRCODE='P4099';
    EXCEPTION WHEN SQLSTATE 'P4099' THEN NULL;
    END;
    IF academic_setup_check.capture(true) IS DISTINCT FROM before_state THEN
        RAISE EXCEPTION 'Snapshot mutation did not roll back';
    END IF;
END $$;
SELECT academic_setup_check.expect_snapshot_change(command) FROM (VALUES
    ('CREATE TRIGGER probe BEFORE INSERT ON public.academic_snapshot_probe '
        'FOR EACH ROW EXECUTE FUNCTION public.academic_snapshot_trigger()'),
    ('ALTER TABLE public.academic_snapshot_probe DISABLE TRIGGER existing_probe'),
    ('ALTER TABLE public.academic_snapshot_probe FORCE ROW LEVEL SECURITY'),
    ('ALTER SEQUENCE public.academic_snapshot_sequence INCREMENT BY 7'),
    ('ALTER SEQUENCE public.academic_snapshot_sequence OWNER TO academic_snapshot_owner'),
    ('GRANT USAGE ON SEQUENCE public.academic_snapshot_sequence TO anon'),
    ('CREATE POLICY probe ON public.academic_snapshot_probe USING (id > 0)'),
    ('CREATE INDEX probe ON public.academic_snapshot_probe(note)'),
    ('ALTER TABLE public.academic_snapshot_probe OWNER TO academic_snapshot_owner'),
    ('GRANT SELECT ON public.academic_snapshot_probe TO anon'),
    ('GRANT UPDATE(note) ON public.academic_snapshot_probe TO anon'),
    ('ALTER FUNCTION public.academic_snapshot_trigger() OWNER TO academic_snapshot_owner'),
    ('REVOKE EXECUTE ON FUNCTION public.academic_snapshot_trigger() FROM PUBLIC'),
    ('GRANT CREATE ON SCHEMA auth TO academic_snapshot_owner'),
    ('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO academic_snapshot_owner')
) changes(command);
ROLLBACK;

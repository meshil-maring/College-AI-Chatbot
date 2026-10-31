BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
-- Future FK actions must never silently delete records or clear a reference.
ALTER TABLE public.programs ADD CONSTRAINT program_deletion_identity UNIQUE(program_id, department_id);
CREATE TABLE workspace_fixture.program_cascade (
    program uuid, owner uuid, is_active boolean DEFAULT false,
    FOREIGN KEY(program, owner) REFERENCES public.programs(program_id, department_id) ON DELETE CASCADE
);
CREATE TABLE workspace_fixture.program_nullable (
    program uuid REFERENCES public.programs(program_id) ON DELETE SET NULL
);
DO $$
DECLARE item jsonb; consumer text;
BEGIN
    FOREACH consumer IN ARRAY ARRAY['program_cascade', 'program_nullable'] LOOP
        item := public.manage_academic_master_record(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'), 'programs', NULL, jsonb_build_object(
                'department_id', workspace_fixture.id('department'), 'name', 'Future linked program',
                'code', consumer, 'degree_type', 'B.Tech', 'duration_years', 4));
        EXECUTE format('INSERT INTO workspace_fixture.%I(program) VALUES($1)', consumer)
            USING (item->>'program_id')::uuid;
        IF consumer = 'program_cascade' THEN
            UPDATE workspace_fixture.program_cascade SET owner = workspace_fixture.id('department');
        END IF;
        BEGIN
            PERFORM public.delete_unused_academic_program(workspace_fixture.id('admin'),
                workspace_fixture.id('tenant'), (item->>'program_id')::uuid);
            RAISE EXCEPTION 'Cascade or set-null consumer was modified';
        EXCEPTION WHEN SQLSTATE 'P2002' THEN NULL; END;
    END LOOP;
END;
$$;

CREATE FUNCTION workspace_fixture.reject_program_deletion_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.action = 'academic.programs.delete' THEN
        RAISE EXCEPTION 'Simulated audit failure' USING ERRCODE = 'P2099';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER program_deletion_test_audit BEFORE INSERT ON public.admin_audit_log
    FOR EACH ROW EXECUTE FUNCTION workspace_fixture.reject_program_deletion_audit();
DO $$
DECLARE item jsonb;
BEGIN
    item := public.manage_academic_master_record(workspace_fixture.id('admin'),
        workspace_fixture.id('tenant'), 'programs', NULL, jsonb_build_object(
            'department_id', workspace_fixture.id('department'), 'name', 'Audit rollback',
            'code', 'AUDIT-ROLLBACK', 'degree_type', 'B.Tech', 'duration_years', 4));
    BEGIN
        PERFORM public.delete_unused_academic_program(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'), (item->>'program_id')::uuid);
        RAISE EXCEPTION 'Audit failure allowed program deletion';
    EXCEPTION WHEN SQLSTATE 'P2099' THEN NULL; END;
    IF NOT EXISTS (SELECT 1 FROM public.programs WHERE program_id = (item->>'program_id')::uuid) THEN
        RAISE EXCEPTION 'Program deletion survived audit failure';
    END IF;
END;
$$;
ROLLBACK;

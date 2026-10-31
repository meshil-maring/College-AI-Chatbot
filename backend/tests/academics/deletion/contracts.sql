-- Run only against the isolated database seeded by academic_workspace/seed.sql.
BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
DO $$
DECLARE
    actor uuid := workspace_fixture.id('admin');
    tenant uuid := workspace_fixture.id('tenant');
    item jsonb;
    child jsonb;
    deleted jsonb;
    active boolean;
    audit_before bigint;
    role_name text;
    accounts_before jsonb;
BEGIN
    SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) INTO accounts_before FROM public.users u;
    FOREACH active IN ARRAY ARRAY[true, false] LOOP
        item := public.manage_academic_master_record(actor, tenant, 'departments', NULL,
            jsonb_build_object('name', 'Unused department', 'code', 'DELETE-' || active, 'is_active', active));
        SELECT count(*) INTO audit_before FROM public.admin_audit_log;
        deleted := public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
        IF deleted <> item OR EXISTS (SELECT 1 FROM public.departments
            WHERE department_id = (item->>'department_id')::uuid) THEN
            RAISE EXCEPTION 'Unused department was not deleted correctly';
        END IF;
        IF (SELECT count(*) FROM public.admin_audit_log) <> audit_before + 1
            OR NOT EXISTS (SELECT 1 FROM public.admin_audit_log
                WHERE action = 'academic.departments.delete' AND record_id = item->>'department_id'
                AND record_data->'before' = item AND record_data->'after' = 'null'::jsonb) THEN
            RAISE EXCEPTION 'Deletion did not audit the before-image exactly once';
        END IF;
        BEGIN
            PERFORM public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
            RAISE EXCEPTION 'Repeated deletion accepted';
        EXCEPTION WHEN no_data_found THEN NULL; END;

        item := public.manage_academic_master_record(actor, tenant, 'departments', NULL,
            jsonb_build_object('name', 'Linked department', 'code', 'LINKED-' || active));
        child := public.manage_academic_master_record(actor, tenant, 'programs', NULL,
            jsonb_build_object('department_id', item->>'department_id', 'name', 'Linked program',
                'code', 'LINKED', 'degree_type', 'B.Tech', 'duration_years', 4, 'is_active', active));
        SELECT count(*) INTO audit_before FROM public.admin_audit_log;
        BEGIN
            PERFORM public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
            RAISE EXCEPTION 'Department with linked program deleted';
        EXCEPTION WHEN SQLSTATE 'P2001' THEN NULL; END;
        IF NOT EXISTS (SELECT 1 FROM public.programs WHERE program_id = (child->>'program_id')::uuid)
            OR (SELECT count(*) FROM public.admin_audit_log) <> audit_before THEN
            RAISE EXCEPTION 'Blocked deletion changed records or audit';
        END IF;

        item := public.manage_academic_master_record(actor, tenant, 'departments', NULL,
            jsonb_build_object('name', 'Subject department', 'code', 'SUBJECT-' || active));
        PERFORM public.manage_academic_master_record(actor, tenant, 'courses', NULL,
            jsonb_build_object('department_id', item->>'department_id', 'name', 'Linked subject',
                'code', 'LINKED', 'credits', 3, 'is_active', active));
        BEGIN
            PERFORM public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
            RAISE EXCEPTION 'Department with linked subject deleted';
        EXCEPTION WHEN SQLSTATE 'P2001' THEN NULL; END;
    END LOOP;

    item := public.manage_academic_master_record(actor, tenant, 'departments', NULL,
        '{"name":"Restricted deletion","code":"RESTRICTED-DELETE"}');
    FOREACH role_name IN ARRAY ARRAY['staff', 'student', 'foreign_admin'] LOOP
        BEGIN
            PERFORM public.delete_unused_academic_department(workspace_fixture.id(role_name),
                tenant, (item->>'department_id')::uuid);
            RAISE EXCEPTION 'Unauthorized actor deleted department';
        EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    END LOOP;
    BEGIN
        PERFORM public.delete_unused_academic_department(workspace_fixture.id('foreign_admin'),
            workspace_fixture.id('foreign_tenant'), (item->>'department_id')::uuid);
        RAISE EXCEPTION 'Foreign department deleted';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        PERFORM public.delete_unused_academic_department(actor, tenant, gen_random_uuid());
        RAISE EXCEPTION 'Missing department accepted';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        DELETE FROM public.role_permissions rp USING public.roles r, public.permissions p
        WHERE rp.role_id = r.id AND rp.permission_id = p.permission_id AND r.name = 'admin'
            AND p.code IN ('departments.manage', 'departments.*', '*');
        PERFORM public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
        RAISE EXCEPTION 'Revoked management permission accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        UPDATE public.institutions SET status = 'suspended' WHERE institution_id = tenant;
        PERFORM public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
        RAISE EXCEPTION 'Suspended institution accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
        PERFORM set_config('request.jwt.claim.role', 'authenticated', true);
        PERFORM public.delete_unused_academic_department(actor, tenant, (item->>'department_id')::uuid);
        RAISE EXCEPTION 'Browser role accepted';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF has_function_privilege('authenticated', 'public.delete_unused_academic_department(uuid,uuid,uuid)', 'EXECUTE')
        OR has_function_privilege('anon', 'public.delete_unused_academic_department(uuid,uuid,uuid)', 'EXECUTE')
        OR NOT has_function_privilege('service_role', 'public.delete_unused_academic_department(uuid,uuid,uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Incorrect deletion RPC grants';
    END IF;
    BEGIN
        PERFORM public.delete_unused_academic_department(actor, tenant, workspace_fixture.id('department'));
        RAISE EXCEPTION 'Department supporting a curriculum, cohort and section was deleted';
    EXCEPTION WHEN SQLSTATE 'P2001' THEN NULL; END;
    IF (SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) FROM public.users u) IS DISTINCT FROM accounts_before THEN
        RAISE EXCEPTION 'Department deletion changed account identities';
    END IF;
END;
$$;

CREATE FUNCTION workspace_fixture.reject_deletion_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.action = 'academic.departments.delete' THEN
        RAISE EXCEPTION 'Simulated audit failure' USING ERRCODE = 'P2099';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER deletion_test_audit BEFORE INSERT ON public.admin_audit_log
    FOR EACH ROW EXECUTE FUNCTION workspace_fixture.reject_deletion_audit();
DO $$
DECLARE item jsonb;
BEGIN
    item := public.manage_academic_master_record(workspace_fixture.id('admin'),
        workspace_fixture.id('tenant'), 'departments', NULL,
        '{"name":"Audit rollback","code":"AUDIT-ROLLBACK"}');
    BEGIN
        PERFORM public.delete_unused_academic_department(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'), (item->>'department_id')::uuid);
        RAISE EXCEPTION 'Failed audit allowed deletion';
    EXCEPTION WHEN SQLSTATE 'P2099' THEN NULL; END;
    IF NOT EXISTS (SELECT 1 FROM public.departments WHERE department_id = (item->>'department_id')::uuid) THEN
        RAISE EXCEPTION 'Department deletion survived an audit failure';
    END IF;
END;
$$;
DROP TRIGGER deletion_test_audit ON public.admin_audit_log;

-- Future cascade and set-null consumers must block deletion too, including a
-- composite reference whose column names differ from the department's columns.
ALTER TABLE public.departments ADD CONSTRAINT deletion_test_identity UNIQUE(department_id, institution_id);
CREATE TABLE workspace_fixture.department_links (
    owner uuid, tenant uuid, is_active boolean DEFAULT false,
    FOREIGN KEY(owner, tenant) REFERENCES public.departments(department_id, institution_id) ON DELETE CASCADE
);
CREATE TABLE workspace_fixture.optional_department_links (
    owner uuid REFERENCES public.departments(department_id) ON DELETE SET NULL
);
DO $$
DECLARE item jsonb; consumer text;
BEGIN
    FOREACH consumer IN ARRAY ARRAY['department_links', 'optional_department_links'] LOOP
        item := public.manage_academic_master_record(workspace_fixture.id('admin'),
            workspace_fixture.id('tenant'), 'departments', NULL,
            jsonb_build_object('name', 'Future consumer', 'code', consumer));
        EXECUTE format('INSERT INTO workspace_fixture.%I(owner) VALUES($1)', consumer)
            USING (item->>'department_id')::uuid;
        IF consumer = 'department_links' THEN
            UPDATE workspace_fixture.department_links SET tenant = workspace_fixture.id('tenant');
        END IF;
        BEGIN
            PERFORM public.delete_unused_academic_department(workspace_fixture.id('admin'),
                workspace_fixture.id('tenant'), (item->>'department_id')::uuid);
            RAISE EXCEPTION 'Cascade or set-null reference was modified';
        EXCEPTION WHEN SQLSTATE 'P2001' THEN NULL; END;
    END LOOP;
END;
$$;
ROLLBACK;

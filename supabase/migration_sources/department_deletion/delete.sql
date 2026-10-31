-- Check every foreign key before deletion, even when its action is CASCADE or
-- SET NULL. Dependency checks include inactive rows and future FK consumers.
CREATE FUNCTION public.delete_unused_academic_department(
    p_actor_user_id uuid, p_institution_id uuid, p_department_id uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    before_row jsonb;
    dependency record;
    linked boolean;
BEGIN
    PERFORM public.assert_academic_foundation_actor(
        p_actor_user_id, p_institution_id, 'departments');
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || p_institution_id::text, 0));
    SELECT to_jsonb(d) INTO before_row FROM public.departments d
    WHERE d.department_id = p_department_id AND d.institution_id = p_institution_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Academic record not found' USING ERRCODE = 'P0002';
    END IF;

    -- The parent row lock also serializes concurrent FK inserts outside our
    -- academic writers. Never rely on a browser's catalogue or status filters.
    FOR dependency IN
        SELECT child_schema.nspname AS schema_name, child_table.relname AS table_name,
            string_agg(format('child.%I = parent.%I', child_column.attname,
                parent_column.attname), ' AND ' ORDER BY keys.position) AS predicate
        FROM pg_catalog.pg_constraint fk
        JOIN pg_catalog.pg_class child_table ON child_table.oid = fk.conrelid
        JOIN pg_catalog.pg_namespace child_schema ON child_schema.oid = child_table.relnamespace
        CROSS JOIN LATERAL unnest(fk.conkey, fk.confkey)
            WITH ORDINALITY AS keys(child_number, parent_number, position)
        JOIN pg_catalog.pg_attribute child_column
            ON child_column.attrelid = fk.conrelid AND child_column.attnum = keys.child_number
        JOIN pg_catalog.pg_attribute parent_column
            ON parent_column.attrelid = fk.confrelid AND parent_column.attnum = keys.parent_number
        WHERE fk.contype = 'f' AND fk.confrelid = 'public.departments'::regclass
        GROUP BY fk.oid, child_schema.nspname, child_table.relname
        ORDER BY child_schema.nspname, child_table.relname
    LOOP
        EXECUTE format(
            'SELECT EXISTS (SELECT 1 FROM %I.%I child JOIN public.departments parent ON %s WHERE parent.department_id = $1)',
            dependency.schema_name, dependency.table_name, dependency.predicate)
        INTO linked USING p_department_id;
        IF linked THEN
            RAISE EXCEPTION 'Department has linked records'
                USING ERRCODE = 'P2001', DETAIL = dependency.table_name;
        END IF;
    END LOOP;

    DELETE FROM public.departments
    WHERE department_id = p_department_id AND institution_id = p_institution_id;
    INSERT INTO public.admin_audit_log(
        actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor_user_id, p_institution_id, 'academic.departments.delete',
        'departments', p_department_id, jsonb_build_object('before', before_row, 'after', NULL));
    RETURN before_row;
END;
$$;

REVOKE ALL ON FUNCTION public.delete_unused_academic_department(uuid, uuid, uuid)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.delete_unused_academic_department(uuid, uuid, uuid)
    TO service_role;
NOTIFY pgrst, 'reload schema';

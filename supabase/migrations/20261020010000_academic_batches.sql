BEGIN;

-- Admission cohorts are managed independently of academic years and subjects.
CREATE TABLE public.academic_batches (
    batch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    program_id uuid NOT NULL REFERENCES public.programs(program_id) ON DELETE RESTRICT,
    start_year integer NOT NULL CHECK (start_year BETWEEN 1900 AND 2200),
    end_year integer NOT NULL CHECK (end_year > start_year AND end_year <= start_year + 10),
    is_active boolean NOT NULL DEFAULT true,
    created_by uuid REFERENCES public.users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, program_id, start_year, end_year),
    UNIQUE (batch_id, institution_id, program_id, start_year, end_year)
);

CREATE FUNCTION public.guard_academic_batch() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (NEW.batch_id, NEW.institution_id, NEW.program_id, NEW.start_year, NEW.end_year)
        IS DISTINCT FROM (OLD.batch_id, OLD.institution_id, OLD.program_id, OLD.start_year, OLD.end_year) THEN
        RAISE EXCEPTION 'Batch identity and admission years are immutable' USING ERRCODE = '22023';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.programs p JOIN public.departments d ON d.department_id = p.department_id
        WHERE p.program_id = NEW.program_id AND d.institution_id = NEW.institution_id
          AND (NOT NEW.is_active OR (p.is_active AND d.is_active))
    ) THEN
        RAISE EXCEPTION 'Batch branch is unavailable in this institution' USING ERRCODE = '23514';
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
CREATE TRIGGER academic_batch_guard BEFORE INSERT OR UPDATE ON public.academic_batches
    FOR EACH ROW EXECUTE FUNCTION public.guard_academic_batch();

-- Preserve only admission cohorts explicitly recorded by the previous flow.
-- Enrollment dates and academic years are not treated as admission evidence.
INSERT INTO public.academic_batches (institution_id, program_id, start_year, end_year, is_active)
SELECT DISTINCT r.institution_id, r.program_id, r.batch_start_year, r.batch_end_year, p.is_active AND d.is_active
FROM public.student_registrations r
JOIN public.programs p ON p.program_id = r.program_id
JOIN public.departments d ON d.department_id = p.department_id AND d.institution_id = r.institution_id;

ALTER TABLE public.student_registrations ADD COLUMN batch_id uuid;
UPDATE public.student_registrations r SET batch_id = b.batch_id
FROM public.academic_batches b
WHERE b.institution_id = r.institution_id AND b.program_id = r.program_id
  AND b.start_year = r.batch_start_year AND b.end_year = r.batch_end_year;
ALTER TABLE public.student_registrations ALTER COLUMN batch_id SET NOT NULL;
ALTER TABLE public.student_registrations ADD CONSTRAINT student_registration_batch_fkey
    FOREIGN KEY (batch_id, institution_id, program_id, batch_start_year, batch_end_year)
    REFERENCES public.academic_batches (batch_id, institution_id, program_id, start_year, end_year) ON DELETE RESTRICT;

CREATE FUNCTION public.guard_student_registration_batch() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    -- A share lock serializes registration with concurrent batch deactivation.
    PERFORM 1 FROM public.academic_batches b
    WHERE b.batch_id = NEW.batch_id AND b.institution_id = NEW.institution_id AND b.program_id = NEW.program_id
      AND b.start_year = NEW.batch_start_year AND b.end_year = NEW.batch_end_year AND b.is_active
    FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'The selected batch is unavailable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER student_registration_batch_guard BEFORE INSERT ON public.student_registrations
    FOR EACH ROW EXECUTE FUNCTION public.guard_student_registration_batch();

CREATE FUNCTION public.manage_academic_batch(
    p_actor_user_id uuid, p_institution_id uuid, p_entity text, p_record_id uuid, p_payload jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    before_row jsonb;
    after_row jsonb;
    item_id uuid := COALESCE(p_record_id, gen_random_uuid());
    field_name text;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    IF NOT EXISTS (
        SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id JOIN public.permissions permission ON permission.permission_id = rp.permission_id
        WHERE ur.user_id = p_actor_user_id AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND r.name = 'admin' AND r.is_active AND permission.is_active
          AND permission.code IN ('departments.manage', 'departments.*', '*')
    ) AND NOT EXISTS (
        SELECT 1 FROM public.user_permission_grants g JOIN public.permissions permission USING (permission_id)
        WHERE g.user_id = p_actor_user_id AND g.institution_id = p_institution_id AND g.revoked_at IS NULL
          AND permission.is_active AND permission.code IN ('departments.manage', 'departments.*', '*')
    ) THEN RAISE EXCEPTION 'Academic management permission required' USING ERRCODE = '42501'; END IF;
    IF p_entity IS DISTINCT FROM 'batches' OR p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' OR p_payload = '{}'::jsonb THEN
        RAISE EXCEPTION 'Batch fields required' USING ERRCODE = '22023';
    END IF;
    FOR field_name IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT field_name = ANY(ARRAY['program_id', 'start_year', 'end_year', 'is_active'])
            OR (p_record_id IS NOT NULL AND field_name <> 'is_active') THEN
            RAISE EXCEPTION 'Unsupported or immutable batch field' USING ERRCODE = '22023';
        END IF;
    END LOOP;
    IF p_payload ? 'is_active' AND jsonb_typeof(p_payload->'is_active') IS DISTINCT FROM 'boolean' THEN
        RAISE EXCEPTION 'Active must be a boolean' USING ERRCODE = '22023';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:' || p_institution_id::text, 0));
    IF p_record_id IS NULL THEN
        IF public.academic_master_tenant('programs', (p_payload->>'program_id')::uuid) IS DISTINCT FROM p_institution_id THEN
            RAISE EXCEPTION 'Branch not found in this institution' USING ERRCODE = 'P0002';
        END IF;
        INSERT INTO public.academic_batches (batch_id, institution_id, program_id, start_year, end_year, is_active, created_by)
        VALUES (item_id, p_institution_id, (p_payload->>'program_id')::uuid, (p_payload->>'start_year')::integer,
                (p_payload->>'end_year')::integer, COALESCE((p_payload->>'is_active')::boolean, true), p_actor_user_id)
        RETURNING to_jsonb(academic_batches.*) INTO after_row;
    ELSE
        SELECT to_jsonb(b) INTO before_row FROM public.academic_batches b
        WHERE b.batch_id = p_record_id AND b.institution_id = p_institution_id FOR UPDATE;
        IF before_row IS NULL THEN RAISE EXCEPTION 'Batch not found' USING ERRCODE = 'P0002'; END IF;
        UPDATE public.academic_batches SET is_active = (p_payload->>'is_active')::boolean
        WHERE batch_id = p_record_id AND institution_id = p_institution_id
        RETURNING to_jsonb(academic_batches.*) INTO after_row;
    END IF;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor_user_id, p_institution_id,
        CASE WHEN p_record_id IS NULL THEN 'academic.batches.create' WHEN p_payload->>'is_active' = 'false' THEN 'academic.batches.deactivate' ELSE 'academic.batches.activate' END,
        'academic_batches', item_id, jsonb_build_object('before', before_row, 'after', after_row));
    RETURN after_row;
END;
$$;

ALTER TABLE public.academic_batches ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.academic_batches FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.academic_batches TO service_role;
REVOKE ALL ON FUNCTION public.guard_academic_batch(), public.guard_student_registration_batch(),
    public.manage_academic_batch(uuid, uuid, text, uuid, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.manage_academic_batch(uuid, uuid, text, uuid, jsonb) TO service_role;

COMMENT ON TABLE public.academic_batches IS 'Branch-specific admission cohorts configured in Academic Setup; archived batches preserve registration history.';
NOTIFY pgrst, 'reload schema';
COMMIT;

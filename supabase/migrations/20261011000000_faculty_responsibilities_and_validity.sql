-- Extend Phase 8.1. Teaching identifiers and revocation history stay intact.
BEGIN;

ALTER TABLE public.faculty_section_assignments
    ADD COLUMN start_at timestamptz,
    ADD COLUMN end_at timestamptz,
    ADD COLUMN is_active boolean NOT NULL DEFAULT true,
    ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
UPDATE public.faculty_section_assignments SET start_at = assigned_at;
ALTER TABLE public.faculty_section_assignments
    ALTER COLUMN start_at SET NOT NULL,
    ALTER COLUMN start_at SET DEFAULT now(),
    ADD CONSTRAINT teaching_valid_interval CHECK (end_at IS NULL OR end_at > start_at);

CREATE TABLE public.responsibility_definitions (
    code text PRIMARY KEY CHECK (btrim(code) <> ''),
    name text NOT NULL,
    allowed_scope_types text[] NOT NULL,
    exclusive_scope boolean NOT NULL DEFAULT true,
    is_active boolean NOT NULL DEFAULT true
);
CREATE TABLE public.responsibility_permissions (
    responsibility_code text NOT NULL REFERENCES public.responsibility_definitions(code),
    permission_id uuid NOT NULL REFERENCES public.permissions(permission_id),
    PRIMARY KEY (responsibility_code, permission_id)
);
CREATE TABLE public.faculty_responsibilities (
    responsibility_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    faculty_user_id uuid NOT NULL REFERENCES public.users(id),
    responsibility_code text NOT NULL REFERENCES public.responsibility_definitions(code),
    scope_type text NOT NULL CHECK (scope_type IN ('institution','department','program','semester','section','course')),
    scope_id uuid NOT NULL,
    department_id uuid REFERENCES public.departments(department_id),
    program_id uuid REFERENCES public.programs(program_id),
    semester_id uuid REFERENCES public.semesters(semester_id),
    academic_year_id uuid REFERENCES public.academic_years(academic_year_id),
    section_id uuid REFERENCES public.sections(section_id),
    section_code text,
    course_id uuid REFERENCES public.courses(course_id),
    scope_key text NOT NULL,
    exclusive_scope boolean NOT NULL DEFAULT true,
    start_at timestamptz NOT NULL,
    end_at timestamptz,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid NOT NULL REFERENCES public.users(id),
    revoked_at timestamptz,
    revoked_by uuid REFERENCES public.users(id),
    CONSTRAINT responsibility_valid_interval CHECK (end_at IS NULL OR end_at > start_at),
    CONSTRAINT responsibility_revocation_pair CHECK ((revoked_at IS NULL) = (revoked_by IS NULL))
);
CREATE INDEX faculty_responsibilities_user_tenant ON public.faculty_responsibilities(faculty_user_id, institution_id);

INSERT INTO public.permissions(name, code, description, scope) VALUES
    ('academic.class.read', 'academic.class.read', 'Read the assigned class academic overview.', 'institution'),
    ('academic.department.read', 'academic.department.read', 'Read the assigned department academic overview.', 'institution'),
    ('academic.reports.read', 'academic.reports.read', 'Read reports in the assigned academic scope.', 'institution'),
    ('attendance.overview.read', 'attendance.overview.read', 'Monitor attendance without teaching edit authority.', 'institution')
ON CONFLICT (code) DO NOTHING;
INSERT INTO public.responsibility_definitions(code, name, allowed_scope_types) VALUES
    ('hod', 'HOD', ARRAY['department']),
    ('class_in_charge', 'Class In-Charge', ARRAY['section']);
INSERT INTO public.responsibility_permissions(responsibility_code, permission_id)
SELECT v.code, p.permission_id FROM (VALUES
    ('hod','academic.department.read'), ('hod','academic.reports.read'),
    ('hod','attendance.overview.read'), ('hod','attendance.read'),
    ('hod','students.read'), ('hod','faculty.read'), ('hod','courses.read'),
    ('hod','departments.read'),
    ('class_in_charge','academic.class.read'), ('class_in_charge','academic.reports.read'),
    ('class_in_charge','attendance.overview.read'), ('class_in_charge','attendance.read'),
    ('class_in_charge','students.read')
) AS v(code, permission) JOIN public.permissions p ON p.code = v.permission;

-- Existing management permission is reused. Platform assignment authority is
-- explicit; this grant does not permit reading tenant attendance data.
INSERT INTO public.role_permissions(role_id, permission_id)
SELECT r.id, p.permission_id FROM public.roles r CROSS JOIN public.permissions p
WHERE r.name = 'super_admin' AND p.code = 'faculty.assignments.manage'
ON CONFLICT DO NOTHING;

-- Scope normalization is enforced even for service-role table writes.
CREATE FUNCTION public.faculty_responsibility_scope_guard()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE
    scope_department uuid;
    scope_institution uuid;
    scope_program uuid;
    scope_semester uuid;
    scope_year uuid;
    scope_section_code text;
    scope_course uuid;
    exclusive boolean;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.revoked_at IS NOT NULL
       AND NEW.institution_id = OLD.institution_id AND NEW.faculty_user_id = OLD.faculty_user_id
       AND NEW.responsibility_code = OLD.responsibility_code AND NEW.scope_type = OLD.scope_type
       AND NEW.scope_id = OLD.scope_id THEN
        NEW.updated_at := now();
        RETURN NEW;
    END IF;
    SELECT exclusive_scope INTO exclusive FROM public.responsibility_definitions
    WHERE code = NEW.responsibility_code AND is_active AND NEW.scope_type = ANY(allowed_scope_types);
    IF NOT FOUND THEN RAISE EXCEPTION 'Invalid responsibility definition or scope' USING ERRCODE = '23514'; END IF;
    IF NEW.scope_type = 'institution' THEN
        scope_institution := NEW.scope_id;
    ELSIF NEW.scope_type = 'department' THEN
        SELECT department_id, institution_id INTO scope_department, scope_institution
        FROM public.departments WHERE department_id = NEW.scope_id AND is_active;
    ELSIF NEW.scope_type = 'program' THEN
        SELECT p.program_id, p.department_id, d.institution_id INTO scope_program, scope_department, scope_institution
        FROM public.programs p JOIN public.departments d USING(department_id)
        WHERE p.program_id = NEW.scope_id AND p.is_active AND d.is_active;
    ELSIF NEW.scope_type = 'semester' THEN
        SELECT p.program_id, p.department_id, d.institution_id, s.semester_id, s.academic_year_id
        INTO scope_program, scope_department, scope_institution, scope_semester, scope_year
        FROM public.programs p JOIN public.departments d USING(department_id) CROSS JOIN public.semesters s
        JOIN public.academic_years ay ON ay.academic_year_id = s.academic_year_id
        WHERE p.program_id = NEW.program_id AND s.semester_id = NEW.scope_id AND p.is_active AND d.is_active AND s.is_active
          AND ay.is_active AND ay.institution_id = d.institution_id;
    ELSIF NEW.scope_type = 'course' THEN
        SELECT c.course_id, c.department_id, d.institution_id INTO scope_course, scope_department, scope_institution
        FROM public.courses c JOIN public.departments d USING(department_id)
        WHERE c.course_id = NEW.scope_id AND c.is_active AND d.is_active;
    ELSIF NEW.scope_type = 'section' THEN
        SELECT c.department_id, d.institution_id, co.program_id, co.semester_id, co.academic_year_id, s.code
        INTO scope_department, scope_institution, scope_program, scope_semester, scope_year, scope_section_code
        FROM public.sections s JOIN public.course_offerings co USING(course_offering_id)
        JOIN public.courses c USING(course_id) JOIN public.departments d ON d.department_id = c.department_id
        JOIN public.programs p ON p.program_id = co.program_id
        JOIN public.departments pd ON pd.department_id = p.department_id
        JOIN public.semesters sem ON sem.semester_id = co.semester_id
        JOIN public.academic_years ay ON ay.academic_year_id = co.academic_year_id
        WHERE s.section_id = NEW.scope_id AND s.is_active AND co.is_active AND c.is_active
          AND d.is_active AND p.is_active AND sem.is_active AND ay.is_active
          AND pd.is_active AND pd.institution_id = d.institution_id
          AND sem.academic_year_id = co.academic_year_id
          AND ay.institution_id = d.institution_id;
    END IF;
    IF scope_institution IS NULL OR scope_institution <> NEW.institution_id OR NOT EXISTS (
        SELECT 1 FROM public.institutions WHERE institution_id = scope_institution AND status = 'active' AND is_active
    ) THEN RAISE EXCEPTION 'Responsibility scope is outside the active institution' USING ERRCODE = '23514'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id WHERE u.id = NEW.faculty_user_id AND u.status = 'active'
        AND r.name = 'faculty' AND r.is_active AND ur.scope_type = 'institution' AND ur.scope_id = NEW.institution_id
    ) THEN RAISE EXCEPTION 'Active Faculty in the institution required' USING ERRCODE = '23514'; END IF;
    NEW.department_id := scope_department;
    NEW.program_id := scope_program;
    NEW.semester_id := scope_semester;
    NEW.academic_year_id := scope_year;
    NEW.section_id := CASE WHEN NEW.scope_type = 'section' THEN NEW.scope_id ELSE NULL END;
    NEW.section_code := scope_section_code;
    NEW.course_id := scope_course;
    NEW.exclusive_scope := exclusive;
    NEW.scope_key := CASE WHEN NEW.scope_type = 'section' THEN
        concat(scope_program, ':', scope_year, ':', scope_semester, ':', scope_section_code)
        WHEN NEW.scope_type = 'semester' THEN concat(scope_program, ':', scope_semester)
        ELSE NEW.scope_id::text END;
    NEW.updated_at := now();
    -- RPCs and table writes serialize appointments for each tenant. The
    -- exclusion constraint below also covers concurrent transaction snapshots.
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(NEW.institution_id::text, 110));
    IF NEW.is_active AND NEW.revoked_at IS NULL AND EXISTS (
        SELECT 1 FROM public.faculty_responsibilities f
        WHERE f.institution_id = NEW.institution_id AND f.responsibility_code = NEW.responsibility_code
        AND f.scope_type = NEW.scope_type AND f.scope_key = NEW.scope_key
        AND f.responsibility_id <> NEW.responsibility_id AND f.is_active AND f.revoked_at IS NULL
        AND (exclusive OR f.faculty_user_id = NEW.faculty_user_id)
        AND tstzrange(f.start_at, f.end_at, '[)') && tstzrange(NEW.start_at, NEW.end_at, '[)')
    ) THEN RAISE EXCEPTION 'Overlapping responsibility appointment' USING ERRCODE = '23P01'; END IF;
    RETURN NEW;
END; $$;
CREATE TRIGGER faculty_responsibility_scope_guard BEFORE INSERT OR UPDATE ON public.faculty_responsibilities
FOR EACH ROW EXECUTE FUNCTION public.faculty_responsibility_scope_guard();

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;
SET LOCAL search_path = public, extensions;
ALTER TABLE public.faculty_responsibilities ADD CONSTRAINT exclusive_faculty_responsibility
EXCLUDE USING gist (institution_id WITH =, responsibility_code WITH =, scope_type WITH =,
    scope_key WITH =, tstzrange(start_at, end_at, '[)') WITH &&)
WHERE (is_active AND revoked_at IS NULL AND exclusive_scope);
ALTER TABLE public.faculty_responsibilities ADD CONSTRAINT duplicate_faculty_responsibility
EXCLUDE USING gist (institution_id WITH =, faculty_user_id WITH =, responsibility_code WITH =,
    scope_type WITH =, scope_key WITH =, tstzrange(start_at, end_at, '[)') WITH &&)
WHERE (is_active AND revoked_at IS NULL);

CREATE FUNCTION public.faculty_assignment_touch()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END; $$;
CREATE TRIGGER faculty_assignment_touch BEFORE UPDATE ON public.faculty_section_assignments
FOR EACH ROW EXECUTE FUNCTION public.faculty_assignment_touch();

CREATE FUNCTION public.manage_faculty_responsibility(
    p_actor_user_id uuid, p_institution_id uuid, p_faculty_user_id uuid,
    p_responsibility_code text, p_scope_type text, p_scope_id uuid,
    p_start_at timestamptz, p_end_at timestamptz, p_is_active boolean,
    p_responsibility_id uuid DEFAULT NULL, p_revoke boolean DEFAULT false,
    p_program_id uuid DEFAULT NULL
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result_id uuid; before_row jsonb; after_row jsonb;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id
        JOIN public.permissions p ON p.permission_id = rp.permission_id
        JOIN public.institutions i ON i.institution_id = p_institution_id
        WHERE u.id = p_actor_user_id AND u.status = 'active' AND r.is_active
        AND p.code = 'faculty.assignments.manage' AND p.is_active AND i.is_active AND i.status = 'active'
        AND ((r.name = 'admin' AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id)
          OR (r.name = 'super_admin' AND ur.scope_type = 'platform' AND ur.scope_id IS NULL))
    ) THEN RAISE EXCEPTION 'Assignment management authority required' USING ERRCODE = '42501'; END IF;
    IF p_actor_user_id = p_faculty_user_id THEN RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501'; END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_institution_id::text, 110));
    IF p_responsibility_id IS NULL THEN
        IF p_revoke THEN RAISE EXCEPTION 'Appointment required' USING ERRCODE = '23514'; END IF;
        INSERT INTO public.faculty_responsibilities(institution_id, faculty_user_id, responsibility_code,
            scope_type, scope_id, program_id, start_at, end_at, is_active, created_by, scope_key)
        VALUES(p_institution_id, p_faculty_user_id, p_responsibility_code, p_scope_type, p_scope_id,
            p_program_id, p_start_at, p_end_at, p_is_active, p_actor_user_id, '')
        RETURNING responsibility_id, to_jsonb(faculty_responsibilities.*) INTO result_id, after_row;
    ELSE
        SELECT to_jsonb(f.*) INTO before_row FROM public.faculty_responsibilities f
        WHERE f.responsibility_id = p_responsibility_id AND f.institution_id = p_institution_id
        AND f.faculty_user_id = p_faculty_user_id AND f.revoked_at IS NULL FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Appointment not found' USING ERRCODE = 'P0002'; END IF;
        IF p_revoke THEN
            -- Revocation must work even if the faculty account or scope has
            -- since been deactivated. The guard skips immutable scope checks.
            UPDATE public.faculty_responsibilities SET revoked_at = now(), revoked_by = p_actor_user_id, is_active = false
            WHERE responsibility_id = p_responsibility_id
            RETURNING responsibility_id, to_jsonb(faculty_responsibilities.*) INTO result_id, after_row;
        ELSE
            UPDATE public.faculty_responsibilities SET scope_type = p_scope_type, scope_id = p_scope_id,
                program_id = p_program_id, start_at = p_start_at, end_at = p_end_at, is_active = p_is_active
            WHERE responsibility_id = p_responsibility_id
            RETURNING responsibility_id, to_jsonb(faculty_responsibilities.*) INTO result_id, after_row;
        END IF;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor_user_id, p_institution_id, CASE WHEN p_revoke THEN 'faculty.responsibility.revoke'
        WHEN before_row IS NULL THEN 'faculty.responsibility.create' ELSE 'faculty.responsibility.update' END,
        'faculty_responsibilities', result_id::text, jsonb_build_object('before',before_row,'after',after_row), 'success');
    RETURN result_id;
END; $$;

CREATE FUNCTION public.update_faculty_teaching_validity(
    p_actor_user_id uuid, p_institution_id uuid, p_assignment_id uuid,
    p_start_at timestamptz, p_end_at timestamptz, p_is_active boolean
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE before_row jsonb; after_row jsonb;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    IF NOT EXISTS (SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id JOIN public.permissions p ON p.permission_id = rp.permission_id
        WHERE ur.user_id = p_actor_user_id AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND r.name = 'admin' AND r.is_active AND p.code = 'faculty.assignments.manage' AND p.is_active)
    THEN RAISE EXCEPTION 'Assignment permission required' USING ERRCODE = '42501'; END IF;
    SELECT to_jsonb(f.*) INTO before_row FROM public.faculty_section_assignments f
        WHERE assignment_id = p_assignment_id AND institution_id = p_institution_id AND revoked_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Teaching assignment not found' USING ERRCODE = 'P0002'; END IF;
    IF (before_row->>'faculty_user_id')::uuid = p_actor_user_id THEN
        RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501'; END IF;
    IF p_is_active AND NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id=u.id JOIN public.roles r ON r.id=ur.role_id
        WHERE u.id=(before_row->>'faculty_user_id')::uuid AND u.status='active' AND r.name='faculty' AND r.is_active
          AND ur.scope_type='institution' AND ur.scope_id=p_institution_id
    ) THEN RAISE EXCEPTION 'Active Faculty in the institution required' USING ERRCODE = '23514'; END IF;
    UPDATE public.faculty_section_assignments SET start_at = p_start_at, end_at = p_end_at, is_active = p_is_active
        WHERE assignment_id = p_assignment_id RETURNING to_jsonb(faculty_section_assignments.*) INTO after_row;
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor_user_id, p_institution_id, 'faculty.assignment.update', 'faculty_section_assignments',
        p_assignment_id::text, jsonb_build_object('before',before_row,'after',after_row), 'success');
    RETURN p_assignment_id;
END; $$;

-- Retain the Phase 8.1 API/RPC contract and its existing audit events while
-- closing self-assignment and revoked management-permission paths.
ALTER FUNCTION public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean)
RENAME TO phase81_manage_faculty_section_assignment_original;
REVOKE ALL ON FUNCTION public.phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)
FROM PUBLIC, anon, authenticated, service_role;
CREATE FUNCTION public.phase81_manage_faculty_section_assignment(
    p_actor_user_id uuid, p_institution_id uuid, p_faculty_user_id uuid, p_section_id uuid,
    p_revoke boolean DEFAULT false
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    IF p_actor_user_id = p_faculty_user_id OR NOT EXISTS (
        SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id JOIN public.permissions p ON p.permission_id = rp.permission_id
        WHERE ur.user_id = p_actor_user_id AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND r.name = 'admin' AND r.is_active AND p.code = 'faculty.assignments.manage' AND p.is_active
    ) THEN RAISE EXCEPTION 'Assignment authority denied' USING ERRCODE = '42501'; END IF;
    IF NOT p_revoke AND NOT EXISTS (
        SELECT 1 FROM public.sections s JOIN public.course_offerings co USING(course_offering_id)
        JOIN public.courses c USING(course_id) JOIN public.departments d ON d.department_id=c.department_id
        JOIN public.programs prog ON prog.program_id=co.program_id
        JOIN public.departments pd ON pd.department_id=prog.department_id
        JOIN public.semesters sem ON sem.semester_id=co.semester_id
        JOIN public.academic_years ay ON ay.academic_year_id=co.academic_year_id
        WHERE s.section_id=p_section_id AND s.is_active AND co.is_active AND c.is_active AND d.is_active
          AND prog.is_active AND pd.is_active AND sem.is_active AND ay.is_active
          AND d.institution_id=p_institution_id AND pd.institution_id=p_institution_id AND ay.institution_id=p_institution_id
          AND sem.academic_year_id=co.academic_year_id
    ) THEN RAISE EXCEPTION 'Active teaching academic scope required' USING ERRCODE = '23514'; END IF;
    RETURN public.phase81_manage_faculty_section_assignment_original(
        p_actor_user_id, p_institution_id, p_faculty_user_id, p_section_id, p_revoke);
END; $$;
REVOKE ALL ON FUNCTION public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.phase81_manage_faculty_section_assignment(uuid,uuid,uuid,uuid,boolean) TO service_role;

CREATE FUNCTION public.create_faculty_teaching_assignment(
    p_actor_user_id uuid, p_institution_id uuid, p_faculty_user_id uuid, p_section_id uuid,
    p_start_at timestamptz, p_end_at timestamptz, p_is_active boolean
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result_id uuid;
BEGIN
    result_id := public.phase81_manage_faculty_section_assignment(p_actor_user_id, p_institution_id,
        p_faculty_user_id, p_section_id, false);
    PERFORM public.update_faculty_teaching_validity(p_actor_user_id, p_institution_id,
        result_id, p_start_at, p_end_at, p_is_active);
    RETURN result_id;
END; $$;
REVOKE ALL ON FUNCTION public.create_faculty_teaching_assignment(uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_faculty_teaching_assignment(uuid,uuid,uuid,uuid,timestamptz,timestamptz,boolean) TO service_role;

ALTER TABLE public.responsibility_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.responsibility_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faculty_responsibilities ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.responsibility_definitions, public.responsibility_permissions, public.faculty_responsibilities FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.responsibility_definitions, public.responsibility_permissions TO service_role;
GRANT SELECT ON public.faculty_responsibilities TO service_role;
REVOKE INSERT, UPDATE, DELETE ON public.responsibility_definitions, public.responsibility_permissions, public.faculty_responsibilities FROM service_role;
REVOKE ALL ON FUNCTION public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.manage_faculty_responsibility(uuid,uuid,uuid,text,text,uuid,timestamptz,timestamptz,boolean,uuid,boolean,uuid) TO service_role;
REVOKE ALL ON FUNCTION public.update_faculty_teaching_validity(uuid,uuid,uuid,timestamptz,timestamptz,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_faculty_teaching_validity(uuid,uuid,uuid,timestamptz,timestamptz,boolean) TO service_role;
COMMIT;

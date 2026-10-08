BEGIN;

INSERT INTO public.responsibility_definitions(code, name, allowed_scope_types)
VALUES
    ('program_coordinator', 'Program Coordinator', ARRAY['program']),
    ('semester_coordinator', 'Semester Coordinator', ARRAY['semester']),
    ('course_coordinator', 'Course Coordinator', ARRAY['course'])
ON CONFLICT (code) DO UPDATE
SET name = EXCLUDED.name,
    allowed_scope_types = EXCLUDED.allowed_scope_types,
    is_active = true;

INSERT INTO public.responsibility_permissions(responsibility_code, permission_id)
SELECT definition.code, permission.permission_id
FROM (VALUES
    ('hod'),
    ('program_coordinator'),
    ('semester_coordinator'),
    ('course_coordinator')
) AS definition(code)
CROSS JOIN public.permissions AS permission
WHERE permission.code = 'faculty.assignments.manage'
  AND permission.is_active
ON CONFLICT (responsibility_code, permission_id) DO NOTHING;

CREATE FUNCTION public.manage_scoped_faculty_teaching_assignment(
    p_actor_user_id uuid,
    p_institution_id uuid,
    p_assignment_id uuid,
    p_faculty_user_id uuid,
    p_section_id uuid,
    p_start_at timestamptz,
    p_end_at timestamptz,
    p_is_active boolean,
    p_revoke boolean DEFAULT false
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    target_faculty uuid;
    target_section uuid;
    target_department uuid;
    target_program uuid;
    target_year uuid;
    target_semester uuid;
    target_section_code text;
    target_course uuid;
    before_row jsonb;
    after_row jsonb;
    result_id uuid;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;

    IF p_actor_user_id = p_faculty_user_id AND p_assignment_id IS NULL THEN
        RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501';
    END IF;

    IF p_assignment_id IS NOT NULL THEN
        SELECT to_jsonb(a.*), a.faculty_user_id, a.section_id
        INTO before_row, target_faculty, target_section
        FROM public.faculty_section_assignments AS a
        WHERE a.assignment_id = p_assignment_id
          AND a.institution_id = p_institution_id
          AND a.revoked_at IS NULL
        FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Teaching assignment not found' USING ERRCODE = 'P0002';
        END IF;
        IF p_actor_user_id = target_faculty THEN
            RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501';
        END IF;
    ELSE
        target_faculty := p_faculty_user_id;
        target_section := p_section_id;
    END IF;

    SELECT c.department_id, co.program_id, co.academic_year_id, co.semester_id,
           s.code, c.course_id
    INTO target_department, target_program, target_year, target_semester,
         target_section_code, target_course
    FROM public.sections AS s
    JOIN public.course_offerings AS co ON co.course_offering_id = s.course_offering_id
    JOIN public.courses AS c ON c.course_id = co.course_id
    JOIN public.departments AS d ON d.department_id = c.department_id
    JOIN public.programs AS prog ON prog.program_id = co.program_id
    JOIN public.departments AS pd ON pd.department_id = prog.department_id
    JOIN public.semesters AS sem ON sem.semester_id = co.semester_id
    JOIN public.academic_years AS ay ON ay.academic_year_id = co.academic_year_id
    WHERE s.section_id = target_section
      AND d.institution_id = p_institution_id
      AND pd.institution_id = p_institution_id
      AND ay.institution_id = p_institution_id
      AND sem.academic_year_id = co.academic_year_id
      AND s.is_active AND co.is_active AND c.is_active AND d.is_active
      AND prog.is_active AND pd.is_active AND sem.is_active AND ay.is_active;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active teaching section in the institution required' USING ERRCODE = '23514';
    END IF;

    PERFORM responsibility.responsibility_id
    FROM public.users AS actor
        JOIN public.user_roles AS ur ON ur.user_id = actor.id
        JOIN public.roles AS role ON role.id = ur.role_id
        JOIN public.faculty_responsibilities AS responsibility
          ON responsibility.faculty_user_id = actor.id
         AND responsibility.institution_id = p_institution_id
        JOIN public.responsibility_definitions AS definition
          ON definition.code = responsibility.responsibility_code
         AND definition.is_active
        JOIN public.responsibility_permissions AS mapping
          ON mapping.responsibility_code = definition.code
        JOIN public.permissions AS permission
          ON permission.permission_id = mapping.permission_id
         AND permission.code = 'faculty.assignments.manage'
         AND permission.is_active
        JOIN public.institutions AS institution
          ON institution.institution_id = p_institution_id
         AND institution.status = 'active'
         AND institution.is_active
        WHERE actor.id = p_actor_user_id
          AND actor.status = 'active'
          AND role.name = 'faculty'
          AND role.is_active
          AND ur.scope_type = 'institution'
          AND ur.scope_id = p_institution_id
          AND responsibility.is_active
          AND responsibility.revoked_at IS NULL
          AND responsibility.start_at <= now()
          AND (responsibility.end_at IS NULL OR now() < responsibility.end_at)
          AND CASE responsibility.scope_type
              WHEN 'department' THEN responsibility.department_id = target_department
              WHEN 'program' THEN responsibility.program_id = target_program
              WHEN 'semester' THEN responsibility.program_id = target_program
                  AND responsibility.academic_year_id = target_year
                  AND responsibility.semester_id = target_semester
              WHEN 'section' THEN responsibility.program_id = target_program
                  AND responsibility.academic_year_id = target_year
                  AND responsibility.semester_id = target_semester
                  AND responsibility.section_code = target_section_code
              WHEN 'course' THEN responsibility.department_id = target_department
                  AND responsibility.course_id = target_course
              ELSE false
          END
    LIMIT 1
    FOR SHARE OF responsibility;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active scoped assignment-management responsibility required' USING ERRCODE = '42501';
    END IF;

    IF p_revoke THEN
        UPDATE public.faculty_section_assignments
        SET revoked_at = now(), revoked_by = p_actor_user_id, is_active = false
        WHERE assignment_id = p_assignment_id
        RETURNING assignment_id, to_jsonb(faculty_section_assignments.*)
        INTO result_id, after_row;
        INSERT INTO public.admin_audit_log(
            actor_user_id, institution_id, action, table_name, record_id, record_data, status
        ) VALUES (
            p_actor_user_id, p_institution_id, 'faculty.assignment.revoke',
            'faculty_section_assignments', result_id::text,
            jsonb_build_object('before', before_row, 'after', after_row), 'success'
        );
        RETURN result_id;
    END IF;

    IF p_start_at IS NULL OR (p_end_at IS NOT NULL AND p_end_at <= p_start_at) THEN
        RAISE EXCEPTION 'Invalid teaching validity interval' USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users AS faculty
        JOIN public.user_roles AS ur ON ur.user_id = faculty.id
        JOIN public.roles AS role ON role.id = ur.role_id
        WHERE faculty.id = target_faculty
          AND faculty.status = 'active'
          AND role.name = 'faculty' AND role.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
    ) THEN
        RAISE EXCEPTION 'Active Faculty member in the institution required' USING ERRCODE = '23514';
    END IF;

    IF p_assignment_id IS NULL THEN
        INSERT INTO public.faculty_section_assignments(
            institution_id, faculty_user_id, section_id, assigned_by,
            start_at, end_at, is_active
        ) VALUES (
            p_institution_id, target_faculty, target_section, p_actor_user_id,
            p_start_at, p_end_at, p_is_active
        )
        RETURNING assignment_id, to_jsonb(faculty_section_assignments.*)
        INTO result_id, after_row;
        INSERT INTO public.admin_audit_log(
            actor_user_id, institution_id, action, table_name, record_id, record_data, status
        ) VALUES (
            p_actor_user_id, p_institution_id, 'faculty.assignment.assign',
            'faculty_section_assignments', result_id::text,
            jsonb_build_object('before', NULL, 'after', after_row), 'success'
        );
    ELSE
        UPDATE public.faculty_section_assignments
        SET start_at = p_start_at, end_at = p_end_at, is_active = p_is_active
        WHERE assignment_id = p_assignment_id
        RETURNING assignment_id, to_jsonb(faculty_section_assignments.*)
        INTO result_id, after_row;
        INSERT INTO public.admin_audit_log(
            actor_user_id, institution_id, action, table_name, record_id, record_data, status
        ) VALUES (
            p_actor_user_id, p_institution_id, 'faculty.assignment.update',
            'faculty_section_assignments', result_id::text,
            jsonb_build_object('before', before_row, 'after', after_row), 'success'
        );
    END IF;
    RETURN result_id;
END;
$$;

REVOKE ALL ON FUNCTION public.manage_scoped_faculty_teaching_assignment(
    uuid, uuid, uuid, uuid, uuid, timestamptz, timestamptz, boolean, boolean
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.manage_scoped_faculty_teaching_assignment(
    uuid, uuid, uuid, uuid, uuid, timestamptz, timestamptz, boolean, boolean
) TO service_role;

COMMIT;

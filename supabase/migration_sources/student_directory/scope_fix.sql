CREATE OR REPLACE FUNCTION public.read_admin_student_directory(
    p_actor uuid,
    p_tenant uuid,
    p_search text,
    p_status text,
    p_program_id uuid,
    p_limit integer,
    p_offset integer
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb;
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.read');
    IF p_limit<1 OR p_limit>100 OR p_offset<0 OR p_offset>1000000 THEN
        RAISE EXCEPTION 'Invalid directory page' USING ERRCODE='22023';
    END IF;
    IF p_status IS NOT NULL AND p_status NOT IN ('pending_sign_in','signed_in','no_signin') THEN
        RAISE EXCEPTION 'Invalid directory status' USING ERRCODE='22023';
    END IF;

    WITH profiles AS (
        SELECT s.student_id AS record_id,
            'student'::text AS record_type,
            coalesce(nullif(btrim(concat_ws(' ',u.first_name,u.last_name)),''),'Unknown student') AS student_name,
            coalesce(s.email,u.email) AS email,
            s.register_number,
            s.university_roll_number,
            CASE WHEN auth_user.last_sign_in_at IS NULL THEN 'no_signin' ELSE 'signed_in' END AS status,
            s.approval_status,
            u.status AS account_status,
            s.status AS student_status,
            s.is_active,
            auth_user.last_sign_in_at,
            NULL::text AS email_delivery_status,
            NULL::timestamptz AS expires_at,
            academic.program_id,
            academic.program_name,
            academic.program_code,
            academic.course_name,
            academic.branch_name,
            academic.branch_code,
            academic.batch_name,
            academic.batch_code,
            academic.section_name,
            academic.section_code,
            academic.admission_cohort_id,
            academic.academic_section_id,
            s.created_at
        FROM public.students s
        LEFT JOIN public.users u ON u.id=s.user_id
        LEFT JOIN auth.users auth_user ON auth_user.id=u.auth_user_id
        LEFT JOIN LATERAL (
            SELECT program.program_id,program.name AS program_name,program.code AS program_code,
                program.degree_type AS course_name,program.name AS branch_name,
                program.code AS branch_code,cohort.name AS batch_name,cohort.code AS batch_code,
                cohort.admission_cohort_id,
                section.name AS section_name,section.code AS section_code,
                section.academic_section_id
            FROM public.student_semester_registrations registration
            JOIN public.academic_sections section
                ON section.academic_section_id=registration.academic_section_id
                AND section.institution_id=p_tenant
            JOIN public.admission_cohorts cohort
                ON cohort.admission_cohort_id=section.admission_cohort_id
                AND cohort.institution_id=p_tenant
            JOIN public.programs program ON program.program_id=cohort.program_id
            JOIN public.departments department
                ON department.department_id=program.department_id
                AND department.institution_id=p_tenant
            JOIN public.semesters term ON term.semester_id=registration.semester_id
            JOIN public.academic_years academic_year
                ON academic_year.academic_year_id=term.academic_year_id
                AND academic_year.institution_id=p_tenant
            WHERE registration.student_id=s.student_id AND registration.institution_id=p_tenant
            ORDER BY term.start_date DESC,registration.assigned_at DESC,
                registration.semester_registration_id
            LIMIT 1
        ) academic ON true
        WHERE s.institution_id=p_tenant
    ), invitations AS (
        SELECT invitation.invitation_id AS record_id,'invitation'::text AS record_type,
            invitation.student_name,invitation.email,invitation.register_number,
            invitation.university_roll_number,
            CASE WHEN auth_user.last_sign_in_at IS NULL
                THEN 'pending_sign_in' ELSE 'signed_in' END AS status,
            NULL::text AS approval_status,NULL::text AS account_status,
            NULL::text AS student_status,NULL::boolean AS is_active,
            auth_user.last_sign_in_at,invitation.email_delivery_status,invitation.expires_at,
            program.program_id,program.name AS program_name,program.code AS program_code,
            program.degree_type AS course_name,program.name AS branch_name,
            program.code AS branch_code,cohort.name AS batch_name,cohort.code AS batch_code,
            cohort.admission_cohort_id,
            section.name AS section_name,section.code AS section_code,
            section.academic_section_id,invitation.created_at
        FROM public.student_onboarding_invitations invitation
        JOIN public.academic_sections section
            ON section.academic_section_id=invitation.academic_section_id
            AND section.institution_id=p_tenant
        JOIN public.admission_cohorts cohort
            ON cohort.admission_cohort_id=section.admission_cohort_id
            AND cohort.institution_id=p_tenant
        JOIN public.programs program ON program.program_id=cohort.program_id
        JOIN public.departments department
            ON department.department_id=program.department_id
            AND department.institution_id=p_tenant
        LEFT JOIN auth.users auth_user ON auth_user.id=invitation.provisioned_auth_user_id
        WHERE invitation.institution_id=p_tenant AND invitation.status='pending'
    ), directory AS (
        SELECT * FROM profiles UNION ALL SELECT * FROM invitations
    ), filtered AS (
        SELECT * FROM directory
        WHERE (nullif(btrim(coalesce(p_search,'')),'') IS NULL OR
            position(lower(btrim(p_search)) IN lower(concat_ws(' ',student_name,email,
                register_number,university_roll_number)))>0)
          AND (p_status IS NULL OR status=p_status)
          AND (p_program_id IS NULL OR program_id=p_program_id)
    ), program_options AS (
        SELECT DISTINCT program_id,program_name,program_code
        FROM directory WHERE program_id IS NOT NULL
    )
    SELECT jsonb_build_object(
        'items',coalesce((
            SELECT jsonb_agg(to_jsonb(page_row) ORDER BY page_row.created_at DESC,
                lower(page_row.student_name),page_row.record_id)
            FROM (
                SELECT * FROM filtered ORDER BY created_at DESC,lower(student_name),record_id
                LIMIT p_limit OFFSET p_offset
            ) page_row
        ),'[]'::jsonb),
        'total',(SELECT count(*) FROM filtered),
        'limit',p_limit,'offset',p_offset,
        'summary',(SELECT jsonb_build_object(
            'total',count(*),
            'pending_sign_in',count(*) FILTER (WHERE status='pending_sign_in'),
            'signed_in',count(*) FILTER (WHERE status='signed_in'),
            'no_signin',count(*) FILTER (WHERE status='no_signin')
        ) FROM directory),
        'programs',(SELECT coalesce(jsonb_agg(jsonb_build_object(
            'program_id',program_id,'program_name',program_name,'program_code',program_code
        ) ORDER BY lower(program_name),program_id),'[]'::jsonb) FROM program_options)
    ) INTO result;
    RETURN result;
END;
$$;
NOTIFY pgrst,'reload schema';

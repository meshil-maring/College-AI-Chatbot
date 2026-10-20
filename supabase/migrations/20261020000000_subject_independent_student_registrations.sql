-- Pre-account class registrations are independent of subject attendance rosters.
-- Academic year/semester identify the authorized class scope; batch is the
-- admission cohort and is never inferred from the current academic year.
CREATE TABLE public.student_registrations (
    registration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    program_id uuid NOT NULL REFERENCES public.programs(program_id) ON DELETE RESTRICT,
    academic_year_id uuid NOT NULL REFERENCES public.academic_years(academic_year_id) ON DELETE RESTRICT,
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id) ON DELETE RESTRICT,
    section_code text NOT NULL CHECK (length(btrim(section_code)) BETWEEN 1 AND 128),
    batch_start_year integer NOT NULL CHECK (batch_start_year BETWEEN 1900 AND 2200),
    batch_end_year integer NOT NULL CHECK (batch_end_year BETWEEN 1901 AND 2210 AND batch_end_year > batch_start_year AND batch_end_year <= batch_start_year + 10),
    register_number text NOT NULL CHECK (length(btrim(register_number)) BETWEEN 1 AND 128),
    university_roll_number text CHECK (university_roll_number IS NULL OR length(btrim(university_roll_number)) BETWEEN 1 AND 128),
    student_name text NOT NULL CHECK (length(btrim(student_name)) BETWEEN 1 AND 256),
    email text CHECK (email IS NULL OR length(email) <= 128),
    address text CHECK (address IS NULL OR length(address) <= 2000),
    created_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, register_number),
    UNIQUE (institution_id, university_roll_number)
);

CREATE INDEX student_registrations_class_scope_idx ON public.student_registrations
    (institution_id, program_id, academic_year_id, semester_id, section_code, register_number);

CREATE FUNCTION public.guard_student_registration_scope() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.programs p
        JOIN public.departments d ON d.department_id = p.department_id
        JOIN public.academic_years y ON y.institution_id = d.institution_id
        JOIN public.semesters s ON s.academic_year_id = y.academic_year_id
        WHERE p.program_id = NEW.program_id AND d.institution_id = NEW.institution_id
          AND y.academic_year_id = NEW.academic_year_id AND s.semester_id = NEW.semester_id
          AND p.is_active AND d.is_active AND y.is_active AND s.is_active
    ) THEN
        RAISE EXCEPTION 'Student registration academic scope is invalid' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER student_registration_scope_guard BEFORE INSERT ON public.student_registrations
    FOR EACH ROW EXECUTE FUNCTION public.guard_student_registration_scope();
ALTER TABLE public.student_registrations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.student_registrations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON public.student_registrations TO service_role;
REVOKE ALL ON FUNCTION public.guard_student_registration_scope() FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE public.student_registrations IS
    'Subject-independent pre-account class registrations. Does not create subject membership, accounts, approval, or admission lifecycle transitions.';

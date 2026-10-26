-- IDs and common foundation/course records survive. Study-semester and class
-- rows stay private for a separately reviewed mapping.
INSERT INTO public.departments (
    department_id, institution_id, name, code, description, is_active, created_at, updated_at
)
SELECT department_id, institution_id, name, code, description, is_active, created_at, updated_at
FROM academic_setup_previous.departments;

INSERT INTO public.programs (
    program_id, department_id, name, code, description, degree_type,
    duration_years, total_credits, is_active, created_at, updated_at
)
SELECT program_id, department_id, name, code, description, degree_type,
       duration_years, total_credits, is_active, created_at, updated_at
FROM academic_setup_previous.programs;

INSERT INTO public.academic_years (
    academic_year_id, institution_id, name, code, start_date, end_date,
    is_current, is_active, created_at, updated_at
)
SELECT academic_year_id, institution_id, name, code, start_date, end_date,
       is_current, is_active, created_at, updated_at
FROM academic_setup_previous.academic_years;

-- Reusable subjects map directly to the export's teaching-course catalogue.
INSERT INTO public.courses (
    course_id, department_id, name, code, description, credits,
    is_active, created_at, updated_at
)
SELECT subject_id, department_id, name, code, description, credits,
       is_active, created_at, updated_at
FROM academic_setup_previous.subjects;

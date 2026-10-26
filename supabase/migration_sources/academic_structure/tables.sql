-- New forward schema after Stage 1; no retired academic tables are restored.
CREATE TABLE public.study_semesters (
    study_semester_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    program_id uuid NOT NULL,
    academic_year_id uuid NOT NULL,
    study_semester_number integer NOT NULL CHECK (study_semester_number BETWEEN 1 AND 30),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 32
        AND code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    description text CHECK (length(description) <= 2000),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (program_id, institution_id)
        REFERENCES public.programs (program_id, institution_id) ON DELETE RESTRICT,
    FOREIGN KEY (academic_year_id, institution_id)
        REFERENCES public.academic_years (academic_year_id, institution_id) ON DELETE RESTRICT,
    UNIQUE (study_semester_id, institution_id),
    UNIQUE (institution_id, program_id, academic_year_id, study_semester_number)
);
CREATE UNIQUE INDEX academic_structure_semester_code
    ON public.study_semesters (institution_id, program_id, academic_year_id, lower(btrim(code)));
CREATE INDEX academic_structure_semester_year
    ON public.study_semesters (institution_id, academic_year_id);

CREATE TABLE public.subjects (
    subject_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    department_id uuid NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 32
        AND code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    description text CHECK (length(description) <= 2000),
    credits numeric NOT NULL CHECK (credits > 0 AND credits <= 100
        AND credits::text NOT IN ('NaN', 'Infinity', '-Infinity')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (department_id, institution_id)
        REFERENCES public.departments (department_id, institution_id) ON DELETE RESTRICT,
    UNIQUE (subject_id, institution_id)
);
CREATE UNIQUE INDEX academic_structure_subject_code
    ON public.subjects (institution_id, department_id, lower(btrim(code)));

COMMENT ON TABLE public.study_semesters IS
    'Degree study progress in one program and academic year; not a dated calendar term.';
COMMENT ON COLUMN public.study_semesters.study_semester_number IS
    'Study sequence, e.g. 5 for Fifth Semester; independent of calendar-term numbering.';
COMMENT ON TABLE public.subjects IS
    'Reusable department-owned subjects, such as Data Mining; distinct from degree programs.';

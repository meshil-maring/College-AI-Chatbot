-- Additive: preserve the eight export tables and their existing APIs and rows.
CREATE TABLE public.program_semesters (
    program_semester_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    program_id uuid NOT NULL REFERENCES public.programs(program_id),
    name text NOT NULL, code text NOT NULL,
    semester_number integer NOT NULL CHECK (semester_number BETWEEN 1 AND 32),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (program_semester_id, institution_id), UNIQUE (program_id, semester_number)
);
CREATE TABLE public.curriculum_versions (
    curriculum_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    program_id uuid NOT NULL REFERENCES public.programs(program_id),
    academic_year_id uuid NOT NULL REFERENCES public.academic_years(academic_year_id),
    name text NOT NULL, version text NOT NULL CHECK (length(btrim(version)) BETWEEN 1 AND 32),
    total_semesters integer NOT NULL CHECK (total_semesters BETWEEN 1 AND 32),
    description text CHECK (length(description) <= 2000),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    is_active boolean NOT NULL DEFAULT true,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (curriculum_version_id, institution_id),
    CHECK ((status='draft' AND published_at IS NULL) OR (status<>'draft' AND published_at IS NOT NULL))
);
CREATE TABLE public.curriculum_subjects (
    curriculum_subject_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    curriculum_version_id uuid NOT NULL,
    program_semester_id uuid NOT NULL,
    course_id uuid NOT NULL REFERENCES public.courses(course_id),
    subject_code text NOT NULL DEFAULT '',
    subject_name text NOT NULL DEFAULT '',
    credits integer,
    lecture_hours integer,
    tutorial_hours integer,
    practical_hours integer,
    course_type text NOT NULL DEFAULT 'core' CHECK (course_type IN ('core','elective','open_elective','skill','project')),
    is_required boolean NOT NULL DEFAULT true, is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (curriculum_subject_id, institution_id), UNIQUE (curriculum_version_id, program_semester_id, course_id),
    FOREIGN KEY (curriculum_version_id, institution_id) REFERENCES public.curriculum_versions(curriculum_version_id, institution_id),
    FOREIGN KEY (program_semester_id, institution_id) REFERENCES public.program_semesters(program_semester_id, institution_id)
);
CREATE TABLE public.admission_cohorts (
    admission_cohort_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    program_id uuid NOT NULL REFERENCES public.programs(program_id),
    curriculum_version_id uuid NOT NULL,
    academic_year_id uuid NOT NULL REFERENCES public.academic_years(academic_year_id),
    name text NOT NULL, code text NOT NULL,
    start_year integer NOT NULL CHECK (start_year BETWEEN 1900 AND 2199),
    end_year integer NOT NULL CHECK (end_year BETWEEN 1901 AND 2200 AND end_year>start_year),
    expected_count integer CHECK (expected_count>=0),
    description text CHECK (length(description)<=2000),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','inactive')),
    is_active boolean GENERATED ALWAYS AS (status='active') STORED,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (admission_cohort_id, institution_id),
    FOREIGN KEY (curriculum_version_id, institution_id) REFERENCES public.curriculum_versions(curriculum_version_id, institution_id)
);
CREATE TABLE public.academic_sections (
    academic_section_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    admission_cohort_id uuid NOT NULL, program_semester_id uuid NOT NULL,
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id),
    name text NOT NULL, code text NOT NULL,
    capacity integer CHECK (capacity>=0), description text CHECK (length(description)<=2000),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (academic_section_id, institution_id),
    FOREIGN KEY (admission_cohort_id, institution_id) REFERENCES public.admission_cohorts(admission_cohort_id, institution_id),
    FOREIGN KEY (program_semester_id, institution_id) REFERENCES public.program_semesters(program_semester_id, institution_id)
);
CREATE TABLE public.academic_offerings (
    academic_offering_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    academic_section_id uuid NOT NULL, curriculum_subject_id uuid NOT NULL,
    capacity integer CHECK (capacity>=0), is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (academic_offering_id, institution_id), UNIQUE (academic_section_id, curriculum_subject_id),
    FOREIGN KEY (academic_section_id, institution_id) REFERENCES public.academic_sections(academic_section_id, institution_id),
    FOREIGN KEY (curriculum_subject_id, institution_id) REFERENCES public.curriculum_subjects(curriculum_subject_id, institution_id)
);
CREATE UNIQUE INDEX program_semesters_code_unique ON public.program_semesters(program_id, lower(btrim(code)));
CREATE UNIQUE INDEX curriculum_versions_version_unique ON public.curriculum_versions(program_id, lower(btrim(version)));
CREATE UNIQUE INDEX admission_cohorts_code_unique ON public.admission_cohorts(institution_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_sections_code_unique ON public.academic_sections(institution_id, lower(btrim(code)));
DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['program_semesters','admission_cohorts','academic_sections'] LOOP
        EXECUTE format('ALTER TABLE public.%I ADD CHECK (length(btrim(name)) BETWEEN 1 AND 160), ADD CHECK (length(btrim(code)) BETWEEN 1 AND 32)',relation_name);
    END LOOP;
    ALTER TABLE public.curriculum_versions ADD CHECK (length(btrim(name)) BETWEEN 1 AND 160);
    FOREACH relation_name IN ARRAY ARRAY['program_semesters','curriculum_versions','curriculum_subjects','admission_cohorts','academic_sections','academic_offerings'] LOOP
        EXECUTE format('CREATE INDEX ON public.%I (institution_id)',relation_name);
    END LOOP;
END;
$$;

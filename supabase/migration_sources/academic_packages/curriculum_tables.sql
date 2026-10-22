-- Ordered source; assembled by the repository migration generator.
CREATE TABLE public.academic_curricula (
    curriculum_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    program_id uuid NOT NULL REFERENCES public.programs(program_id),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 64),
    version integer NOT NULL CHECK (version BETWEEN 1 AND 1000),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_by uuid NOT NULL REFERENCES public.users(id),
    UNIQUE (curriculum_id, institution_id)
);
CREATE UNIQUE INDEX academic_curriculum_code_version ON public.academic_curricula
    (institution_id, program_id, lower(btrim(code)), version);

CREATE TABLE public.academic_curriculum_subjects (
    curriculum_subject_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    curriculum_id uuid NOT NULL REFERENCES public.academic_curricula(curriculum_id),
    study_semester integer NOT NULL CHECK (study_semester BETWEEN 1 AND 30),
    course_id uuid NOT NULL REFERENCES public.courses(course_id),
    course_type text NOT NULL CHECK (course_type IN ('core','elective','open_elective','skill','project')),
    is_core boolean NOT NULL DEFAULT false,
    UNIQUE (curriculum_id, study_semester, course_id),
    UNIQUE (curriculum_subject_id, curriculum_id, study_semester)
);
CREATE TABLE public.academic_subject_packages (
    package_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    curriculum_id uuid NOT NULL REFERENCES public.academic_curricula(curriculum_id),
    study_semester integer NOT NULL CHECK (study_semester BETWEEN 1 AND 30),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 64),
    UNIQUE (package_id, curriculum_id, study_semester)
);
CREATE UNIQUE INDEX academic_package_code ON public.academic_subject_packages
    (curriculum_id, study_semester, lower(btrim(code)));
CREATE TABLE public.academic_package_subjects (
    package_id uuid NOT NULL REFERENCES public.academic_subject_packages(package_id),
    curriculum_subject_id uuid NOT NULL REFERENCES public.academic_curriculum_subjects(curriculum_subject_id),
    PRIMARY KEY (package_id, curriculum_subject_id)
);

CREATE TABLE public.academic_classes (
    class_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    batch_id uuid NOT NULL REFERENCES public.academic_batches(batch_id),
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id),
    study_semester integer NOT NULL CHECK (study_semester BETWEEN 1 AND 30),
    curriculum_id uuid NOT NULL,
    section_code text NOT NULL CHECK (length(btrim(section_code)) BETWEEN 1 AND 128),
    code text NOT NULL UNIQUE,
    student_choice_enabled boolean NOT NULL DEFAULT false,
    teaching_start timestamptz NOT NULL,
    teaching_end timestamptz NOT NULL,
    change_cutoff timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_by uuid NOT NULL REFERENCES public.users(id),
    FOREIGN KEY (curriculum_id, institution_id)
        REFERENCES public.academic_curricula(curriculum_id, institution_id),
    CHECK (teaching_start < teaching_end),
    CHECK (change_cutoff >= teaching_start
        AND change_cutoff <= teaching_start + (teaching_end - teaching_start) / 2),
    UNIQUE (class_id, institution_id),
    UNIQUE (class_id, curriculum_id, study_semester),
    UNIQUE (institution_id, batch_id, semester_id, section_code)
);
CREATE TABLE public.academic_class_packages (
    class_id uuid NOT NULL REFERENCES public.academic_classes(class_id),
    package_id uuid NOT NULL REFERENCES public.academic_subject_packages(package_id),
    selection_code text NOT NULL UNIQUE,
    enabled boolean NOT NULL DEFAULT true,
    PRIMARY KEY (class_id, package_id)
);
CREATE UNIQUE INDEX academic_class_normalized_section ON public.academic_classes
    (institution_id, batch_id, semester_id, lower(btrim(section_code)));
CREATE TABLE public.academic_class_subjects (
    class_id uuid NOT NULL REFERENCES public.academic_classes(class_id),
    curriculum_subject_id uuid NOT NULL REFERENCES public.academic_curriculum_subjects(curriculum_subject_id),
    section_id uuid NOT NULL REFERENCES public.sections(section_id),
    PRIMARY KEY (class_id, curriculum_subject_id),
    UNIQUE (class_id, section_id)
);
CREATE INDEX academic_class_subject_section ON public.academic_class_subjects(section_id);
CREATE TABLE public.academic_class_responsibilities (
    class_id uuid NOT NULL REFERENCES public.academic_classes(class_id),
    responsibility_id uuid NOT NULL REFERENCES public.faculty_responsibilities(responsibility_id),
    PRIMARY KEY (class_id, responsibility_id)
);

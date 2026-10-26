-- Class sections belong to a program/year study semester, never to a subject.
CREATE TABLE public.class_sections (
    section_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    study_semester_id uuid NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 32
        AND code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    description text CHECK (length(description) <= 2000),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (study_semester_id, institution_id)
        REFERENCES public.study_semesters (study_semester_id, institution_id) ON DELETE RESTRICT,
    UNIQUE (section_id, institution_id)
);
CREATE UNIQUE INDEX academic_sections_context_code
    ON public.class_sections (institution_id, study_semester_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_sections_context_name
    ON public.class_sections (institution_id, study_semester_id, lower(btrim(name)));

CREATE TABLE public.section_subject_assignments (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    section_id uuid NOT NULL,
    subject_id uuid NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (section_id, institution_id)
        REFERENCES public.class_sections (section_id, institution_id) ON DELETE RESTRICT,
    FOREIGN KEY (subject_id, institution_id)
        REFERENCES public.subjects (subject_id, institution_id) ON DELETE RESTRICT,
    UNIQUE (institution_id, section_id, subject_id)
);
CREATE INDEX academic_sections_assigned_subject
    ON public.section_subject_assignments (institution_id, subject_id);

COMMENT ON TABLE public.class_sections IS
    'Class-level sections; program and academic year derive from their immutable study semester.';
COMMENT ON TABLE public.section_subject_assignments IS
    'Multiple reusable subjects per class section; removal deactivates a link and preserves its subject.';

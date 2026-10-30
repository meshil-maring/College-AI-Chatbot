-- One required selection per group; each option is an indivisible subject set.
CREATE TABLE public.curriculum_choice_groups (
    choice_group_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    curriculum_version_id uuid NOT NULL,
    program_semester_id uuid NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    UNIQUE (choice_group_id, institution_id),
    FOREIGN KEY (curriculum_version_id, institution_id)
        REFERENCES public.curriculum_versions(curriculum_version_id, institution_id),
    FOREIGN KEY (program_semester_id, institution_id)
        REFERENCES public.program_semesters(program_semester_id, institution_id),
    UNIQUE (curriculum_version_id, program_semester_id, name)
);
CREATE TABLE public.curriculum_choice_options (
    choice_option_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL,
    choice_group_id uuid NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    UNIQUE (choice_option_id, institution_id),
    UNIQUE (choice_group_id, name),
    FOREIGN KEY (choice_group_id, institution_id)
        REFERENCES public.curriculum_choice_groups(choice_group_id, institution_id) ON DELETE CASCADE
);
CREATE TABLE public.curriculum_choice_subjects (
    institution_id uuid NOT NULL,
    choice_option_id uuid NOT NULL,
    curriculum_subject_id uuid NOT NULL,
    PRIMARY KEY (choice_option_id, curriculum_subject_id),
    FOREIGN KEY (choice_option_id, institution_id)
        REFERENCES public.curriculum_choice_options(choice_option_id, institution_id) ON DELETE CASCADE,
    FOREIGN KEY (curriculum_subject_id, institution_id)
        REFERENCES public.curriculum_subjects(curriculum_subject_id, institution_id)
);
CREATE TABLE public.student_semester_registrations (
    semester_registration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    student_id uuid NOT NULL REFERENCES public.students(student_id),
    academic_section_id uuid NOT NULL,
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id),
    selected_option_ids uuid[] NOT NULL DEFAULT '{}',
    status text NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned', 'registered')),
    assigned_at timestamptz NOT NULL DEFAULT now(),
    registered_at timestamptz,
    UNIQUE (semester_registration_id, institution_id),
    UNIQUE (student_id, semester_id),
    FOREIGN KEY (academic_section_id, institution_id)
        REFERENCES public.academic_sections(academic_section_id, institution_id),
    CHECK ((status='assigned' AND registered_at IS NULL) OR
           (status='registered' AND registered_at IS NOT NULL))
);
CREATE TABLE public.student_offering_enrollments (
    offering_enrollment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL,
    semester_registration_id uuid NOT NULL,
    academic_offering_id uuid NOT NULL,
    -- Preserve the subject identity and credits that the student registered for.
    subject_snapshot jsonb NOT NULL,
    enrolled_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (semester_registration_id, academic_offering_id),
    FOREIGN KEY (semester_registration_id, institution_id)
        REFERENCES public.student_semester_registrations(semester_registration_id, institution_id),
    FOREIGN KEY (academic_offering_id, institution_id)
        REFERENCES public.academic_offerings(academic_offering_id, institution_id)
);
CREATE INDEX ON public.curriculum_choice_groups (institution_id);
CREATE INDEX ON public.curriculum_choice_options (institution_id);
CREATE INDEX ON public.curriculum_choice_subjects (institution_id, curriculum_subject_id);
CREATE INDEX ON public.student_semester_registrations (institution_id, academic_section_id);
CREATE INDEX ON public.student_offering_enrollments (institution_id, academic_offering_id);

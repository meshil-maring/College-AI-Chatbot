-- One current Head of Department per department. Ended appointments are kept
-- as history; a new appointment never rewrites an earlier row.
CREATE TABLE public.department_heads (
    department_head_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    department_id uuid NOT NULL,
    faculty_user_id uuid NOT NULL REFERENCES public.users(id),
    assigned_by uuid NOT NULL REFERENCES public.users(id),
    assigned_at timestamptz NOT NULL DEFAULT now(),
    ended_by uuid REFERENCES public.users(id),
    ended_at timestamptz,
    -- Deployed departments/programs expose only a primary key; tenant ownership
    -- is checked by assign_department_head and the transfer commands.
    FOREIGN KEY (department_id) REFERENCES public.departments(department_id),
    CONSTRAINT department_heads_end_pair CHECK ((ended_at IS NULL) = (ended_by IS NULL))
);
CREATE UNIQUE INDEX department_heads_one_current
    ON public.department_heads (department_id) WHERE ended_at IS NULL;
CREATE INDEX department_heads_faculty
    ON public.department_heads (institution_id, faculty_user_id) WHERE ended_at IS NULL;

-- A request moves one current-term semester registration to another section.
-- The from/to sections and the pre-transfer registration are retained as the
-- student's placement history after approval.
CREATE TABLE public.student_transfer_requests (
    transfer_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    student_id uuid NOT NULL REFERENCES public.students(student_id),
    transfer_type text NOT NULL CHECK (transfer_type IN ('section_transfer', 'program_transfer')),
    semester_registration_id uuid NOT NULL,
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id),
    from_section_id uuid NOT NULL,
    to_section_id uuid NOT NULL,
    from_program_id uuid NOT NULL,
    to_program_id uuid NOT NULL,
    to_department_id uuid NOT NULL,
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 10 AND 2000),
    status text NOT NULL DEFAULT 'submitted'
        CHECK (status IN ('submitted', 'under_review', 'approved', 'rejected', 'cancelled')),
    submitted_by uuid NOT NULL REFERENCES public.users(id),
    submitted_at timestamptz NOT NULL DEFAULT now(),
    review_started_by uuid REFERENCES public.users(id),
    review_started_at timestamptz,
    decided_by uuid REFERENCES public.users(id),
    decided_at timestamptz,
    decided_as text CHECK (decided_as IN ('admin', 'hod')),
    decision_comment text CHECK (length(decision_comment) <= 2000),
    cancelled_at timestamptz,
    previous_registration jsonb,
    previous_enrollments jsonb NOT NULL DEFAULT '[]'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (transfer_request_id, institution_id),
    FOREIGN KEY (semester_registration_id, institution_id)
        REFERENCES public.student_semester_registrations(semester_registration_id, institution_id),
    FOREIGN KEY (from_section_id, institution_id)
        REFERENCES public.academic_sections(academic_section_id, institution_id),
    FOREIGN KEY (to_section_id, institution_id)
        REFERENCES public.academic_sections(academic_section_id, institution_id),
    -- Program and department are copied from tenant-filtered sections.
    FOREIGN KEY (from_program_id) REFERENCES public.programs(program_id),
    FOREIGN KEY (to_program_id) REFERENCES public.programs(program_id),
    FOREIGN KEY (to_department_id) REFERENCES public.departments(department_id),
    CONSTRAINT student_transfer_distinct_section CHECK (from_section_id <> to_section_id),
    CONSTRAINT student_transfer_decision CHECK (
        (status IN ('approved', 'rejected'))
        = (decided_at IS NOT NULL AND decided_by IS NOT NULL AND decided_as IS NOT NULL)),
    CONSTRAINT student_transfer_rejection_reason CHECK (
        status <> 'rejected' OR length(btrim(COALESCE(decision_comment, ''))) > 0),
    CONSTRAINT student_transfer_cancelled CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL))
);
CREATE UNIQUE INDEX student_transfer_one_open
    ON public.student_transfer_requests (student_id) WHERE status IN ('submitted', 'under_review');
CREATE INDEX student_transfer_queue
    ON public.student_transfer_requests (institution_id, status, submitted_at DESC);
CREATE INDEX student_transfer_department
    ON public.student_transfer_requests (institution_id, to_department_id, status);

CREATE TABLE public.student_transfer_events (
    transfer_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL,
    transfer_request_id uuid NOT NULL,
    actor_user_id uuid NOT NULL REFERENCES public.users(id),
    action text NOT NULL
        CHECK (action IN ('submitted', 'review_started', 'approved', 'rejected', 'cancelled')),
    comment text CHECK (length(comment) <= 2000),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (transfer_request_id, institution_id)
        REFERENCES public.student_transfer_requests(transfer_request_id, institution_id)
);
CREATE INDEX student_transfer_events_request
    ON public.student_transfer_events (transfer_request_id, created_at);

COMMENT ON TABLE public.department_heads IS
    'Current and ended Head of Department appointments; HODs decide transfers into their department.';
COMMENT ON TABLE public.student_transfer_requests IS
    'Student section and program transfer requests. Approval reassigns the current-term registration.';
COMMENT ON TABLE public.student_transfer_events IS
    'Append-only history of submission, review, decision and cancellation for each transfer request.';

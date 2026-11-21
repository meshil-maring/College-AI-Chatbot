-- Student Academic Transfer System
-- Additive schema for transfer requests, subject equivalencies,
-- academic placement history and institutional transfer settings.
-- No existing table, function, constraint, or migration is modified or removed.
BEGIN;

-- ============================================================================
-- 1. Institution-level transfer configuration
-- ============================================================================
CREATE TABLE public.institution_transfer_settings (
    institution_id uuid PRIMARY KEY REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    allow_student_transfer_requests boolean NOT NULL DEFAULT false,
    allow_staff_created_transfers boolean NOT NULL DEFAULT true,
    max_active_requests_per_student integer NOT NULL DEFAULT 1
        CHECK (max_active_requests_per_student > 0 AND max_active_requests_per_student <= 100),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.institution_transfer_settings IS
    'Per-institution configuration governing who may submit academic transfer requests.';

-- ============================================================================
-- 2. Subject equivalency mechanism (curriculum mapping for transfers)
-- ============================================================================
CREATE TABLE public.subject_equivalencies (
    equivalency_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    source_subject_id uuid NOT NULL REFERENCES public.subjects(subject_id) ON DELETE RESTRICT,
    target_subject_id uuid NOT NULL REFERENCES public.subjects(subject_id) ON DELETE RESTRICT,
    program_id uuid NOT NULL REFERENCES public.programs(program_id) ON DELETE RESTRICT,
    equivalence_type text NOT NULL
        CHECK (equivalence_type IN ('same', 'approved_equivalent', 'repeat_required', 'additional_required')),
    source_credits numeric CHECK (source_credits > 0 AND source_credits <= 100),
    target_credits numeric CHECK (target_credits > 0 AND target_credits <= 100),
    credit_comparison text CHECK (credit_comparison IN ('equal', 'less', 'greater')),
    approved_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    approved_at timestamptz,
    notes text CHECK (length(notes) <= 2000),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution_id, source_subject_id, target_subject_id)
);

COMMENT ON TABLE public.subject_equivalencies IS
    'Approved subject equivalencies used to assess academic transfer eligibility.';

-- ============================================================================
-- 3. Historical academic placements (one active placement per student)
-- ============================================================================
CREATE TABLE public.student_academic_placements (
    placement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.students(student_id) ON DELETE CASCADE,
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    program_id uuid NOT NULL REFERENCES public.programs(program_id) ON DELETE RESTRICT,
    batch_id uuid REFERENCES public.academic_batches(batch_id) ON DELETE RESTRICT,
    section_id uuid REFERENCES public.academic_sections(academic_section_id) ON DELETE RESTRICT,
    semester_id uuid REFERENCES public.semesters(semester_id) ON DELETE RESTRICT,
    curriculum_version_id uuid REFERENCES public.curriculum_versions(curriculum_version_id) ON DELETE RESTRICT,
    is_active boolean NOT NULL DEFAULT true,
    effective_from date NOT NULL,
    effective_to date,
    created_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (placement_id, institution_id),
    CONSTRAINT student_academic_placements_effective_order
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX one_active_placement_per_student
    ON public.student_academic_placements (student_id) WHERE is_active;

COMMENT ON TABLE public.student_academic_placements IS
    'Versioned academic placement history. A completed transfer creates a new active placement while previous placements and their academic records remain unchanged.';

-- ============================================================================
-- 4. Transfer requests
-- ============================================================================
CREATE TABLE public.transfer_requests (
    request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES public.students(student_id) ON DELETE CASCADE,
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    transfer_type text NOT NULL
        CHECK (transfer_type IN ('program_transfer', 'section_transfer', 'semester_placement')),
    current_program_id uuid NOT NULL REFERENCES public.programs(program_id),
    current_batch_id uuid REFERENCES public.academic_batches(batch_id),
    current_section_id uuid REFERENCES public.academic_sections(academic_section_id),
    current_semester_id uuid REFERENCES public.semesters(semester_id),
    current_curriculum_version_id uuid REFERENCES public.curriculum_versions(curriculum_version_id),
    target_program_id uuid NOT NULL REFERENCES public.programs(program_id),
    target_batch_id uuid REFERENCES public.academic_batches(batch_id),
    target_section_id uuid REFERENCES public.academic_sections(academic_section_id),
    target_semester_id uuid REFERENCES public.semesters(semester_id),
    target_curriculum_version_id uuid REFERENCES public.curriculum_versions(curriculum_version_id),
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 4000),
    supporting_documents jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL DEFAULT 'submitted'
        CHECK (status IN ('submitted', 'under_review', 'eligible', 'not_eligible', 'approved', 'rejected', 'completed', 'cancelled')),
    eligibility_status text
        CHECK (eligibility_status IN ('eligible', 'not_eligible', 'manual_review', 'pending')),
    eligibility_notes text CHECK (length(eligibility_notes) <= 2000),
    suggested_target_semester_id uuid REFERENCES public.semesters(semester_id),
    reviewed_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    reviewed_at timestamptz,
    review_comments text CHECK (length(review_comments) <= 2000),
    approved_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    approved_at timestamptz,
    approved_reason text CHECK (length(approved_reason) <= 2000),
    rejected_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    rejected_at timestamptz,
    rejection_reason text CHECK (length(rejection_reason) <= 2000),
    effective_date date,
    completed_at timestamptz,
    completed_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    created_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (request_id, institution_id)
);

CREATE INDEX transfer_requests_student_status
    ON public.transfer_requests (student_id, institution_id, status);
CREATE INDEX transfer_requests_institution_status
    ON public.transfer_requests (institution_id, status, created_at DESC);

COMMENT ON TABLE public.transfer_requests IS
    'Student academic transfer requests and their approval lifecycle.';

-- ============================================================================
-- 5. Transfer request action history (audit within a transfer)
-- ============================================================================
CREATE TABLE public.transfer_request_actions (
    action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid NOT NULL REFERENCES public.transfer_requests(request_id) ON DELETE CASCADE,
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    actor_user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    action text NOT NULL
        CHECK (action IN ('submitted', 'reviewed', 'approved', 'rejected', 'completed', 'cancelled')),
    comments text CHECK (length(comments) <= 2000),
    from_status text,
    to_status text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (action_id, institution_id)
);

CREATE INDEX transfer_request_actions_request
    ON public.transfer_request_actions (request_id, created_at);

COMMENT ON TABLE public.transfer_request_actions IS
    'Immutable history of every submission, review, approval, rejection and completion on a transfer request.';

-- ============================================================================
-- Security: service-role is the server trust boundary; browser roles have no
-- direct access. The service layer performs all authorization and tenant
-- checks before mutating through the service-role client.
-- ============================================================================
DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'institution_transfer_settings',
        'subject_equivalencies',
        'student_academic_placements',
        'transfer_requests',
        'transfer_request_actions'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', relation_name);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO service_role', relation_name);
    END LOOP;
END $$;

COMMIT;

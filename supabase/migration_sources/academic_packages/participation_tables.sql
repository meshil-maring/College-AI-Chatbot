ALTER TABLE public.faculty_attendance_rosters
    ADD COLUMN participation_active boolean NOT NULL DEFAULT true,
    ADD COLUMN participation_ended_at timestamptz;

CREATE TABLE public.academic_class_placements (
    placement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id uuid NOT NULL REFERENCES public.academic_classes(class_id),
    registration_id uuid NOT NULL REFERENCES public.student_registrations(registration_id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_by uuid NOT NULL REFERENCES public.users(id),
    UNIQUE (registration_id, class_id)
);
CREATE INDEX academic_placement_class ON public.academic_class_placements(class_id);
CREATE TABLE public.academic_package_assignments (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    placement_id uuid NOT NULL UNIQUE REFERENCES public.academic_class_placements(placement_id),
    package_id uuid NOT NULL REFERENCES public.academic_subject_packages(package_id),
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    assigned_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    assigned_by uuid NOT NULL REFERENCES public.users(id),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE public.academic_package_revisions (
    revision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id uuid NOT NULL REFERENCES public.academic_package_assignments(assignment_id),
    revision integer NOT NULL CHECK (revision > 0),
    package_id uuid NOT NULL REFERENCES public.academic_subject_packages(package_id),
    actor_user_id uuid NOT NULL REFERENCES public.users(id),
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 2000),
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (assignment_id, revision)
);
CREATE TABLE public.academic_subject_participation (
    participation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    placement_id uuid NOT NULL REFERENCES public.academic_class_placements(placement_id),
    curriculum_subject_id uuid NOT NULL REFERENCES public.academic_curriculum_subjects(curriculum_subject_id),
    roster_id uuid NOT NULL REFERENCES public.faculty_attendance_rosters(roster_id) ON DELETE RESTRICT,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    revision_id uuid NOT NULL REFERENCES public.academic_package_revisions(revision_id),
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);
CREATE UNIQUE INDEX academic_subject_one_active ON public.academic_subject_participation
    (placement_id, curriculum_subject_id) WHERE ended_at IS NULL;
CREATE INDEX academic_participation_roster ON public.academic_subject_participation(roster_id);
CREATE TABLE public.academic_package_requests (
    request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id uuid NOT NULL REFERENCES public.academic_package_assignments(assignment_id),
    source_revision integer NOT NULL CHECK (source_revision > 0),
    package_id uuid NOT NULL REFERENCES public.academic_subject_packages(package_id),
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 2000),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','expired','superseded')),
    requested_by uuid NOT NULL REFERENCES public.users(id),
    requested_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    reviewed_by uuid REFERENCES public.users(id),
    reviewed_at timestamptz,
    decision_reason text CHECK (decision_reason IS NULL OR length(btrim(decision_reason)) BETWEEN 1 AND 2000)
);
CREATE UNIQUE INDEX academic_one_pending_request ON public.academic_package_requests(assignment_id)
    WHERE status = 'pending';

-- All mutation authority is in owner-executed RPCs; RLS is defense in depth.
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'academic_curricula','academic_curriculum_subjects','academic_subject_packages',
        'academic_package_subjects','academic_classes','academic_class_packages',
        'academic_class_subjects','academic_class_responsibilities','academic_class_placements',
        'academic_package_assignments','academic_package_revisions','academic_subject_participation',
        'academic_package_requests'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC, anon, authenticated, service_role', table_name);
    END LOOP;
END;
$$;

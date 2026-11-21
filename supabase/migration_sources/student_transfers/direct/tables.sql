-- Direct transfers are made by an administrator or a Head of Department and
-- apply immediately. They reuse the request row as placement history.
ALTER TABLE public.student_transfer_requests
    ADD COLUMN initiated_by text NOT NULL DEFAULT 'student'
        CHECK (initiated_by IN ('student', 'admin', 'hod'));

ALTER TABLE public.student_transfer_events
    DROP CONSTRAINT student_transfer_events_action_check,
    ADD CONSTRAINT student_transfer_events_action_check CHECK (action IN (
        'submitted', 'review_started', 'approved', 'rejected', 'cancelled', 'transferred'));

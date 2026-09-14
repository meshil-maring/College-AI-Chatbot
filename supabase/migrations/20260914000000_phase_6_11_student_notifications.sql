-- ============================================================================
-- Phase 6.11 — Student notifications / academic alerts
-- ============================================================================
-- Secure student notification and academic-alert foundation.
--
-- Every notification belongs to exactly one student and one institution.
-- The institution is server-derived from the authenticated/authoritative
-- student context (Phase 6.9). Clients NEVER supply student_id,
-- user_id, or institution_id for ownership decisions.
--
-- Notification types use a controlled vocabulary (CHECK constraint).
-- Read state is a boolean (is_read) with a NOT NULL default.
-- Duplicate academic-event notifications are prevented via a UNIQUE
-- constraint on (student_id, source_record_id, notification_type).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- student_notifications
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS "public".student_notifications (
    notification_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    student_id           UUID      NOT NULL
        REFERENCES "public".students(student_id) ON DELETE CASCADE,

    institution_id       UUID      NOT NULL
        REFERENCES "public".institutions(institution_id),

    notification_type    VARCHAR(32) NOT NULL
        CHECK (notification_type IN (
            'attendance_alert',
            'result_published',
            'academic_status',
            'academic_admin'
        )),

    title                VARCHAR(255) NOT NULL,
    message              TEXT         NOT NULL,

    is_read              BOOLEAN     NOT NULL DEFAULT FALSE,

    source_type          VARCHAR(64) NOT NULL DEFAULT 'academic_event',
    source_record_id     UUID,

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at              TIMESTAMPTZ
);


-- ----------------------------------------------------------------------------
-- Indexes
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_student_notifications_student
    ON "public".student_notifications (student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_student_notifications_institution
    ON "public".student_notifications (institution_id);

CREATE INDEX IF NOT EXISTS idx_student_notifications_read
    ON "public".student_notifications (student_id, is_read)
    WHERE NOT is_read;


-- ----------------------------------------------------------------------------
-- Idempotency: prevent duplicate academic-event notifications
-- (same student + same source record + same notification type)
-- ----------------------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_student_notification_source_record
    ON "public".student_notifications (student_id, source_record_id, notification_type)
    WHERE source_record_id IS NOT NULL;


-- ----------------------------------------------------------------------------
-- Tenant guard trigger — mirrors the pattern used by attendance/result
-- tables in Phases 6.7 / 6.8. The institution_id is always derived from
-- the student record; the client can never supply or override it.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION trg_student_notifications_tenant_guard()
RETURNS TRIGGER AS $$
DECLARE
    student_institution_id UUID;
BEGIN
    -- Derive institution_id from the student record (server authority).
    SELECT students.institution_id
        INTO student_institution_id
        FROM "public".students
        WHERE students.student_id = NEW.student_id
        LIMIT 1;

    IF student_institution_id IS NULL THEN
        RAISE EXCEPTION 'Student not found'
            USING ERRCODE = 'F404',
                  MESSAGE = 'Student not found';
    END IF;

    -- If the client supplied an institution_id, it MUST match the student's.
    IF NEW.institution_id IS NOT NULL
        AND NEW.institution_id != student_institution_id THEN
        RAISE EXCEPTION 'Tenant mismatch'
            USING ERRCODE = 'F403',
                  MESSAGE = 'notification.institution_id does not match student tenant';
    END IF;

    -- Set / override institution_id from the student record.
    NEW.institution_id := student_institution_id;

    -- read_at is maintained by the application layer; guard against
    -- inconsistent state here as a backstop.
    IF NEW.is_read AND NEW.read_at IS NULL THEN
        NEW.read_at := now();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trg_student_notifications_tenant_guard
    BEFORE INSERT OR UPDATE ON "public".student_notifications
    FOR EACH ROW
    EXECUTE FUNCTION trg_student_notifications_tenant_guard();


-- ----------------------------------------------------------------------------
-- Grant service-role access (consistent with other Phase Admin-1 tables)
-- ----------------------------------------------------------------------------

GRANT SELECT, INSERT, UPDATE, DELETE
    ON "public".student_notifications
    TO "service_role";

-- ============================================================================
-- Backfill guard: existing rows (none expected) would have their
-- institution_id corrected by the trigger on any subsequent update.
-- ============================================================================

COMMENT ON TABLE "public".student_notifications IS
    'Student notifications and academic alerts (Phase 6.11)';

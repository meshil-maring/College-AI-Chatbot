-- ============================================================================
-- Phase 6.7 — Attendance Data (tenant-safe hardening of student_attendance)
-- ============================================================================
-- Phase 6.7 does NOT create a new attendance table: the existing
-- ``public.student_attendance`` table (Phase Admin-1 migration
-- 20260909000000) already provides the daily per-student/section attendance
-- rows, the status vocabulary CHECK, the (student_id, section_id, date)
-- uniqueness rule, and the student foreign key. This migration is purely
-- ADDITIVE hardening so attendance satisfies the Phase 6.7 requirements:
--
--   1. tenant association  -> a server-derived ``institution_id`` column
--      whose value always equals ``students.institution_id``. It is filled by
--      a BEFORE INSERT/UPDATE trigger from the STUDENT record — never from
--      the client — and cross-referenced against the section's institution so
--      a row can never pair a student and a section from different
--      institutions.
--   2. updated timestamp  -> ``updated_at`` matches the project-wide
--      convention (every other Phase Admin-1 table carries created_at +
--      updated_at). The guard trigger refreshes it on every UPDATE.
--   3. academic-context integrity -> attendance.academic_year_id/semester_id
--      must describe the SAME offering as the section (section →
--      course_offerings). This is safely verifiable with existing structures.
--   4. ownership immutability -> student_id / section_id / academic_year_id /
--      semester_id can never be reassigned by an UPDATE.
--
-- No locked Phase 6.1-6.6 migration is modified. No new tables are created.
-- Application-layer authorization (RBAC + tenant) remains the current model;
-- these triggers are a database-level safety net, not a replacement.
-- ============================================================================

-- A. institution_id (server-derived canonical tenant key)
-- ---------------------------------------------------------------------------
-- The canonical tenant key remains students.institution_id (Phase 6.1/6.6
-- locks). We DENORMALIZE it onto the attendance row ONLY so queries can scope
-- tenant-safely and the FK/trigger guarantee the invariant; the trigger
-- overrides any caller-supplied value, so it is never client-controlled.

ALTER TABLE "public"."student_attendance"
    ADD COLUMN "institution_id" "uuid";

-- Backfill existing rows from their student records (FK integrity guarantees
-- every row has exactly one student).
UPDATE "public"."student_attendance" AS "sa"
SET "institution_id" = "s"."institution_id"
FROM "public"."students" AS "s"
WHERE "sa"."student_id" = "s"."student_id";

ALTER TABLE "public"."student_attendance"
    ALTER COLUMN "institution_id" SET NOT NULL;

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_institution_id_fkey"
    FOREIGN KEY ("institution_id")
    REFERENCES "public"."institutions" ("institution_id");

-- B. updated_at (project-wide convention: mutable rows track last change)
-- ---------------------------------------------------------------------------

ALTER TABLE "public"."student_attendance"
    ADD COLUMN "updated_at" timestamp with time zone;

UPDATE "public"."student_attendance" SET "updated_at" = "created_at";

ALTER TABLE "public"."student_attendance"
    ALTER COLUMN "updated_at" SET DEFAULT "now"();

ALTER TABLE "public"."student_attendance"
    ALTER COLUMN "updated_at" SET NOT NULL;

-- C. Database guard function + trigger
-- ---------------------------------------------------------------------------
-- Invariants enforced at the database layer (independent of application code):
--   * institution_id is ALWAYS derived from students.institution_id.
--   * the section must exist and its institution must equal the student's
--     institution (no cross-institution attendance rows).
--   * academic_year_id / semester_id must match the section's offering.
--   * UPDATE may not reassign student_id / section_id / academic_year_id /
--     semester_id (ownership fields are immutable); updated_at is refreshed.
-- Trigger functions bypass EXECUTE grants (invoked by the server), so no
-- additional GRANT is needed.

CREATE OR REPLACE FUNCTION "public"."student_attendance_tenant_guard"()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
DECLARE
    v_student_institution_id uuid;
    v_section_institution_id uuid;
    v_section_academic_year_id uuid;
    v_section_semester_id uuid;
BEGIN
    -- Resolve the student's canonical tenant; the row is anchored to it.
    SELECT "institution_id" INTO v_student_institution_id
    FROM "public"."students"
    WHERE "student_id" = NEW."student_id";

    IF v_student_institution_id IS NULL THEN
        RAISE EXCEPTION 'student % does not exist', NEW."student_id";
    END IF;

    -- Resolve the section's academic context and institution via
    -- section -> course_offering -> course -> department.
    SELECT "co"."academic_year_id", "co"."semester_id", "d"."institution_id"
    INTO v_section_academic_year_id, v_section_semester_id, v_section_institution_id
    FROM "public"."sections" AS "sec"
    JOIN "public"."course_offerings" AS "co"
        ON "co"."course_offering_id" = "sec"."course_offering_id"
    JOIN "public"."courses" AS "c"
        ON "c"."course_id" = "co"."course_id"
    JOIN "public"."departments" AS "d"
        ON "d"."department_id" = "c"."department_id"
    WHERE "sec"."section_id" = NEW."section_id";

    IF v_section_academic_year_id IS NULL THEN
        RAISE EXCEPTION 'section % does not exist', NEW."section_id";
    END IF;

    -- Tenant is always server-derived — override any caller-supplied value.
    NEW."institution_id" := v_student_institution_id;

    IF v_section_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'attendance student and section belong to different institutions';
    END IF;

    IF NEW."academic_year_id" IS DISTINCT FROM v_section_academic_year_id
       OR NEW."semester_id" IS DISTINCT FROM v_section_semester_id THEN
        RAISE EXCEPTION 'attendance academic context must match the section offering';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF NEW."student_id"      IS DISTINCT FROM OLD."student_id"
           OR NEW."section_id"    IS DISTINCT FROM OLD."section_id"
           OR NEW."academic_year_id" IS DISTINCT FROM OLD."academic_year_id"
           OR NEW."semester_id"   IS DISTINCT FROM OLD."semester_id" THEN
            RAISE EXCEPTION 'attendance ownership fields cannot be changed';
        END IF;
        NEW."updated_at" := "now"();
    END IF;

    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS "trg_student_attendance_tenant_guard"
    ON "public"."student_attendance";

CREATE TRIGGER "trg_student_attendance_tenant_guard"
    BEFORE INSERT OR UPDATE ON "public"."student_attendance"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."student_attendance_tenant_guard"();

-- D. Indexes (justified query patterns)
-- ---------------------------------------------------------------------------
-- * tenant-scoped management lists/dashboardizing by institution;
-- * the existing student/date ordering used by list_student_attendance;
-- * the academic-year/semester filter used by admin and student reads.

CREATE INDEX IF NOT EXISTS "idx_student_attendance_institution_id"
    ON "public"."student_attendance" ("institution_id");

CREATE INDEX IF NOT EXISTS "idx_student_attendance_student_date"
    ON "public"."student_attendance" ("student_id", "date");

CREATE INDEX IF NOT EXISTS "idx_student_attendance_ay_semester"
    ON "public"."student_attendance" ("academic_year_id", "semester_id");

-- E. Column comments ---------------------------------------------------------

COMMENT ON COLUMN "public"."student_attendance"."institution_id"
    IS 'Canonical tenant key denormalized onto the attendance row. Always equals students.institution_id; maintained by the student_attendance_tenant_guard trigger and never trusted from the client.';

COMMENT ON COLUMN "public"."student_attendance"."updated_at"
    IS 'Last modification timestamp, refreshed by the student_attendance_tenant_guard trigger on UPDATE.';

-- ============================================================================
-- ROLLBACK (inverse DDL — apply manually only if this phase is reverted)
-- ============================================================================
-- DROP TRIGGER IF EXISTS "trg_student_attendance_tenant_guard"
--     ON "public"."student_attendance";
-- DROP FUNCTION IF EXISTS "public"."student_attendance_tenant_guard"();
-- DROP INDEX IF EXISTS "idx_student_attendance_institution_id";
-- DROP INDEX IF EXISTS "idx_student_attendance_student_date";
-- DROP INDEX IF EXISTS "idx_student_attendance_ay_semester";
-- ALTER TABLE "public"."student_attendance"
--     DROP CONSTRAINT "student_attendance_institution_id_fkey";
-- ALTER TABLE "public"."student_attendance"
--     ALTER COLUMN "updated_at" DROP DEFAULT,
--     DROP COLUMN "updated_at";
-- ALTER TABLE "public"."student_attendance"
--     DROP COLUMN "institution_id";
-- ============================================================================
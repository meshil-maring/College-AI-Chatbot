-- ============================================================================
-- Phase 6.2 — Student Database Model (Student Identity Extension)
-- ============================================================================
-- Extends the EXISTING public.students table (Phase Admin-1) with the identity
-- columns required for multi-identifier student authentication (email /
-- register number / university roll number) and the registration-approval
-- lifecycle consumed by later Phase 6 phases.
--
-- ARCHITECTURE DECISIONS
--
--   * institution_id remains the sole canonical tenant key (Phase 6.1 lock).
--     No tenant_id column, no tenant relationship, and no second student
--     table is introduced. Every change below is additive to the existing
--     students row.
--   * Academic identity uniqueness is INSTITUTION-SCOPED, not global:
--         College A -> register_number = 1001
--         College B -> register_number = 1001
--     may coexist because academic identifiers are assigned per institution.
--     The same rule now applies to student_number: the pre-existing GLOBAL
--     "students_student_number_key" constraint contradicted the documented
--     product rule ("student_number is institution-assigned and unique across
--     the institution"), so it is replaced with an (institution_id,
--     student_number) unique constraint.
--   * Email: account-level login-email uniqueness is already owned by
--     public.users.email (globally UNIQUE since the Phase 3 baseline) plus
--     Supabase Auth (GoTrue). students.email stores the institutional student
--     email identity with institution-scoped uniqueness so institutional
--     namespaces stay independent. No password column is added anywhere:
--     authentication remains delegated to Supabase Auth (Phase 6.5 owns
--     login behavior).
--   * approval_status represents the registration lifecycle
--         pending -> approved | rejected
--     independently of the pre-existing academic "status"
--     (active/inactive/graduated/withdrawn) and "is_active" (soft-archive)
--     fields. No overlapping status fields were modified or removed.
--   * New identity columns are NULLABLE: existing rows have no values and
--     Phase 6.5 (student authentication) defines when they become required.
--     CHECK constraints reject empty/whitespace values and non-lowercase
--     emails so future identity lookups stay deterministic.
--   * Reversible: every change has an inverse documented in the ROLLBACK
--     section at the end of this file.
--
-- DATA PRESERVATION (verified read-only against the remote database before
-- authoring): 3 existing student rows, all institution ...0001 (GIT), status
-- 'active', is_active true; zero (institution_id, student_number) duplicate
-- pairs; zero global student_number duplicates; zero email duplicates in
-- public.users. No identity values are modified and no rows are deleted; the
-- only existing-row change is the explicit approval_status backfill in
-- section D.
-- ============================================================================

-- A. New identity + approval columns ----------------------------------------

ALTER TABLE "public"."students"
    ADD COLUMN "email" "text";

ALTER TABLE "public"."students"
    ADD COLUMN "register_number" "text";

ALTER TABLE "public"."students"
    ADD COLUMN "university_roll_number" "text";

ALTER TABLE "public"."students"
    ADD COLUMN "approval_status" "text" DEFAULT 'pending'::"text" NOT NULL;

-- B. Value constraints -------------------------------------------------------
-- NULL is permitted (identity provisioning completes in Phase 6.5); empty or
-- whitespace-only values and non-lowercase emails are rejected.

ALTER TABLE "public"."students"
    ADD CONSTRAINT "students_email_check"
    CHECK (("email" IS NULL) OR ("email" = "btrim"("lower"("email"))));

ALTER TABLE "public"."students"
    ADD CONSTRAINT "students_register_number_check"
    CHECK (("register_number" IS NULL)
        OR ("btrim"("register_number") <> ''::"text"));

ALTER TABLE "public"."students"
    ADD CONSTRAINT "students_university_roll_number_check"
    CHECK (("university_roll_number" IS NULL)
        OR ("btrim"("university_roll_number") <> ''::"text"));

ALTER TABLE "public"."students"
    ADD CONSTRAINT "students_approval_status_check"
    CHECK (("approval_status" = ANY (ARRAY[
        'pending'::"text",
        'approved'::"text",
        'rejected'::"text"
    ])));

-- C. Uniqueness (institution-scoped) ----------------------------------------
-- Verified collision-free read-only before authoring (see header). NULL
-- identity values remain repeatable within an institution (Postgres NULLs
-- are distinct in unique constraints), matching the nullable-until-Phase-6.5
-- design.

ALTER TABLE ONLY "public"."students"
    DROP CONSTRAINT "students_student_number_key";

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_student_number_key"
    UNIQUE ("institution_id", "student_number");

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_email_key"
    UNIQUE ("institution_id", "email");

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_register_number_key"
    UNIQUE ("institution_id", "register_number");

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_university_roll_number_key"
    UNIQUE ("institution_id", "university_roll_number");

-- D. Backfill existing rows --------------------------------------------------
-- The three existing students were provisioned by the Phase Admin-1 demo
-- migration (admin action, not self-registration), so they are approved by
-- definition. The column default stays 'pending' to match the upcoming
-- self-registration -> pending -> approval -> approved -> login flow.

UPDATE "public"."students"
SET "approval_status" = 'approved'
WHERE "approval_status" = 'pending';

-- E. Indexes (justified future lookup patterns) ------------------------------
-- * Single-column identifier indexes support identifier-only lookups
--   (identifier supplied without an institution context).
-- * The unique constraints in section C already back institution-scoped
--   (institution_id, identifier) lookups.
-- * The (institution_id, approval_status) index supports the future admin
--   approval-queue pattern (list my institution's pending registrations).
-- * idx_students_institution_id already exists (Phase Admin-1).

CREATE INDEX IF NOT EXISTS "idx_students_email"
    ON "public"."students" ("email");

CREATE INDEX IF NOT EXISTS "idx_students_register_number"
    ON "public"."students" ("register_number");

CREATE INDEX IF NOT EXISTS "idx_students_university_roll_number"
    ON "public"."students" ("university_roll_number");

CREATE INDEX IF NOT EXISTS "idx_students_institution_approval"
    ON "public"."students" ("institution_id", "approval_status");

-- F. Column comments ---------------------------------------------------------

COMMENT ON COLUMN "public"."students"."email"
    IS 'Institutional student email identity (lowercase); institution-scoped unique. Account-level login email uniqueness is owned by public.users.email and Supabase Auth.';
COMMENT ON COLUMN "public"."students"."register_number"
    IS 'Institution-assigned register number; unique within institution_id.';
COMMENT ON COLUMN "public"."students"."university_roll_number"
    IS 'University-assigned roll number; unique within institution_id.';
COMMENT ON COLUMN "public"."students"."approval_status"
    IS 'Registration lifecycle state (pending/approved/rejected); independent of the academic status and is_active fields.';

-- ============================================================================
-- ROLLBACK (inverse DDL — apply manually only if this phase is reverted)
-- ============================================================================
-- UPDATE "public"."students" SET "approval_status" = 'pending';
--
-- ALTER TABLE "public"."students"
--     DROP CONSTRAINT "students_institution_id_student_number_key",
--     DROP CONSTRAINT "students_institution_id_email_key",
--     DROP CONSTRAINT "students_institution_id_register_number_key",
--     DROP CONSTRAINT "students_institution_id_university_roll_number_key",
--     DROP CONSTRAINT "students_email_check",
--     DROP CONSTRAINT "students_register_number_check",
--     DROP CONSTRAINT "students_university_roll_number_check",
--     DROP CONSTRAINT "students_approval_status_check",
--     DROP COLUMN "email",
--     DROP COLUMN "register_number",
--     DROP COLUMN "university_roll_number",
--     DROP COLUMN "approval_status";
--
-- DROP INDEX IF EXISTS "idx_students_email";
-- DROP INDEX IF EXISTS "idx_students_register_number";
-- DROP INDEX IF EXISTS "idx_students_university_roll_number";
-- DROP INDEX IF EXISTS "idx_students_institution_approval";
--
-- ALTER TABLE ONLY "public"."students"
--     ADD CONSTRAINT "students_student_number_key" UNIQUE ("student_number");
-- ============================================================================

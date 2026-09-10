-- ============================================================================
-- Phase Admin-1 - Database Foundation (Admin & Student Academic Schema)
-- ============================================================================
--
-- Creates eight new tables that support the Admin module and the authenticated
-- student "My Academics" endpoints:
--
--   1. students              - Student profile, linked one-to-one to users.user_id
--   2. student_results       - Consolidated per-semester result summaries
--   3. student_result_items  - Individual course-grade rows within a result
--   4. test_results          - Per-test / per-exam scores for a student
--   5. student_attendance    - Daily attendance records per student-section
--   6. faqs                  - Frequently-asked-questions (global or per-institution)
--   7. notices               - Notice / announcement board entries
--   8. admin_audit_log       - Audit trail of privileged admin actions
--
-- DESIGN PRINCIPLES
--
--   * Additive - no existing table, function, constraint, or index is modified.
--   * FK references use the ACTUAL primary-key column names in the remote
--     database (e.g. users.user_id, roles.role_id - NOT the stale "id" names
--     found in schemaV2_export.sql).
--   * Student academic data is NEVER injected into the RAG pipeline.
--   * Student endpoints resolve identity from the authenticated JWT; no
--     client-supplied student_id is accepted for "my" data.
--   * Every new table is granted to service_role (the existing convention).
--
-- SEED DATA
--
--   Demo administrator account + role assignment.
--   Three demo students (auth users + profiles + role assignments).
--   Reference academic records: results, result items, test scores,
--   attendance, FAQs, notices, and an audit-log entry.
--
-- ============================================================================
-- A. students
-- ============================================================================
-- Links a public.users row to student-specific academic metadata.
-- One user -> at most one student profile (UNIQUE user_id).
-- student_number is institution-assigned and unique across the institution.

CREATE TABLE IF NOT EXISTS "public"."students" (
    "student_id"              uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id"                 uuid  NOT NULL,
    "institution_id"          uuid  NOT NULL,
    "student_number"          text  NOT NULL,
    "program_id"              uuid,
    "academic_year_id"        uuid,
    "enrollment_date"         date  NOT NULL,
    "expected_graduation_date" date,
    "status"                  text  DEFAULT 'active'::text NOT NULL,
    "is_active"               boolean DEFAULT true NOT NULL,
    "created_at"              timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"              timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "students_student_number_check"
        CHECK (("btrim"("student_number") <> ''::text)),
    CONSTRAINT "students_status_check"
        CHECK (("status" = ANY (ARRAY[
            'active'::text,
            'inactive'::text,
            'graduated'::text,
            'withdrawn'::text
        ]))),
    CONSTRAINT "students_graduation_date_check"
        CHECK (("expected_graduation_date" IS NULL)
            OR ("expected_graduation_date" >= "enrollment_date"))
);

ALTER TABLE "public"."students" OWNER TO "postgres";

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_pkey" PRIMARY KEY ("student_id");

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_user_id_key" UNIQUE ("user_id");

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_student_number_key" UNIQUE ("student_number");

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_fkey"
    FOREIGN KEY ("institution_id")
    REFERENCES "public"."institutions" ("institution_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_program_id_fkey"
    FOREIGN KEY ("program_id")
    REFERENCES "public"."programs" ("program_id")
    ON DELETE SET NULL;

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_academic_year_id_fkey"
    FOREIGN KEY ("academic_year_id")
    REFERENCES "public"."academic_years" ("academic_year_id")
    ON DELETE SET NULL;

ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_user_id_fkey"
    FOREIGN KEY ("user_id")
    REFERENCES "public"."users" ("user_id")
    ON DELETE CASCADE;

-- ============================================================================
-- B. student_results
-- ============================================================================
-- Consolidated result summary for a student in a given academic-year/semester.
-- One row per (student, academic_year, semester, program) combination.

CREATE TABLE IF NOT EXISTS "public"."student_results" (
    "student_result_id"     uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id"            uuid  NOT NULL,
    "academic_year_id"      uuid  NOT NULL,
    "semester_id"           uuid  NOT NULL,
    "program_id"            uuid  NOT NULL,
    "result_type"           text  NOT NULL,
    "total_credits_earned"  numeric(6,2),
    "total_credits_max"     numeric(6,2),
    "sgpa"                  numeric(4,2),
    "cgpa"                  numeric(4,2),
    "status"                text  DEFAULT 'published'::text NOT NULL,
    "issued_at"             timestamp with time zone,
    "created_at"            timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"            timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "student_results_result_type_check"
        CHECK (("result_type" = ANY (ARRAY[
            'semester'::text,
            'supplementary'::text,
            'final'::text,
            'provisional'::text
        ]))),
    CONSTRAINT "student_results_status_check"
        CHECK (("status" = ANY (ARRAY[
            'draft'::text,
            'published'::text,
            'withheld'::text
        ]))),
    CONSTRAINT "student_results_credits_check"
        CHECK (("total_credits_earned" IS NULL) OR ("total_credits_earned" >= 0)),
    CONSTRAINT "student_results_sgpa_check"
        CHECK (("sgpa" IS NULL) OR ("sgpa" >= 0)),
    CONSTRAINT "student_results_cgpa_check"
        CHECK (("cgpa" IS NULL) OR ("cgpa" >= 0))
);

ALTER TABLE "public"."student_results" OWNER TO "postgres";

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_pkey" PRIMARY KEY ("student_result_id");

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_student_sem_ay_prog_key"
    UNIQUE ("student_id", "academic_year_id", "semester_id", "program_id");

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_student_id_fkey"
    FOREIGN KEY ("student_id")
    REFERENCES "public"."students" ("student_id")
    ON DELETE CASCADE;

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_academic_year_id_fkey"
    FOREIGN KEY ("academic_year_id")
    REFERENCES "public"."academic_years" ("academic_year_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_semester_id_fkey"
    FOREIGN KEY ("semester_id")
    REFERENCES "public"."semesters" ("semester_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_program_id_fkey"
    FOREIGN KEY ("program_id")
    REFERENCES "public"."programs" ("program_id")
    ON DELETE RESTRICT;

-- ============================================================================
-- C. student_result_items
-- ============================================================================
-- Individual course-grade rows within a student_result.

CREATE TABLE IF NOT EXISTS "public"."student_result_items" (
    "student_result_item_id" uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "student_result_id"      uuid  NOT NULL,
    "course_id"              uuid  NOT NULL,
    "section_id"             uuid,
    "credits_earned"         numeric(5,2),
    "credits_max"            numeric(5,2),
    "grade_points"           numeric(5,2),
    "letter_grade"           text,
    "grade_value"            numeric(5,2),
    "status"                 text  DEFAULT 'completed'::text NOT NULL,
    "created_at"             timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "student_result_items_status_check"
        CHECK (("status" = ANY (ARRAY[
            'completed'::text,
            'incomplete'::text,
            'withdrawn'::text,
            'not_attempted'::text
        ]))),
    CONSTRAINT "student_result_items_credits_check"
        CHECK (("credits_earned" IS NULL) OR ("credits_earned" >= 0)),
    CONSTRAINT "student_result_items_grade_points_check"
        CHECK (("grade_points" IS NULL) OR ("grade_points" >= 0))
);

ALTER TABLE "public"."student_result_items" OWNER TO "postgres";

ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_pkey" PRIMARY KEY ("student_result_item_id");

ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_result_course_key"
    UNIQUE ("student_result_id", "course_id");

ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_student_result_id_fkey"
    FOREIGN KEY ("student_result_id")
    REFERENCES "public"."student_results" ("student_result_id")
    ON DELETE CASCADE;

ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_course_id_fkey"
    FOREIGN KEY ("course_id")
    REFERENCES "public"."courses" ("course_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_section_id_fkey"
    FOREIGN KEY ("section_id")
    REFERENCES "public"."sections" ("section_id")
    ON DELETE SET NULL;

-- ============================================================================
-- D. test_results
-- ============================================================================
-- Per-test / per-exam scores for a student.

CREATE TABLE IF NOT EXISTS "public"."test_results" (
    "test_result_id"       uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id"           uuid  NOT NULL,
    "course_id"            uuid  NOT NULL,
    "section_id"           uuid,
    "academic_year_id"     uuid  NOT NULL,
    "semester_id"          uuid  NOT NULL,
    "test_name"            text  NOT NULL,
    "test_type"            text  NOT NULL,
    "max_marks"            numeric(8,2) NOT NULL,
    "scored_marks"         numeric(8,2),
    "percentage"           numeric(5,2),
    "letter_grade"         text,
    "conducted_at"         timestamp with time zone,
    "status"               text  DEFAULT 'published'::text NOT NULL,
    "created_at"           timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"           timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "test_results_test_name_check"
        CHECK (("btrim"("test_name") <> ''::text)),
    CONSTRAINT "test_results_test_type_check"
        CHECK (("test_type" = ANY (ARRAY[
            'quiz'::text,
            'assignment'::text,
            'midterm'::text,
            'final'::text,
            'project'::text,
            'internal'::text,
            'external'::text
        ]))),
    CONSTRAINT "test_results_max_marks_check"
        CHECK (("max_marks" > 0)),
    CONSTRAINT "test_results_scored_marks_check"
        CHECK (("scored_marks" IS NULL) OR ("scored_marks" >= 0)),
    CONSTRAINT "test_results_percentage_check"
        CHECK (("percentage" IS NULL) OR ("percentage" >= 0 AND "percentage" <= 100)),
    CONSTRAINT "test_results_status_check"
        CHECK (("status" = ANY (ARRAY[
            'draft'::text,
            'published'::text,
            'withheld'::text
        ])))
);

ALTER TABLE "public"."test_results" OWNER TO "postgres";

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_pkey" PRIMARY KEY ("test_result_id");

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_student_course_test_sem_key"
    UNIQUE ("student_id", "course_id", "test_name", "academic_year_id", "semester_id");

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_student_id_fkey"
    FOREIGN KEY ("student_id")
    REFERENCES "public"."students" ("student_id")
    ON DELETE CASCADE;

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_course_id_fkey"
    FOREIGN KEY ("course_id")
    REFERENCES "public"."courses" ("course_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_section_id_fkey"
    FOREIGN KEY ("section_id")
    REFERENCES "public"."sections" ("section_id")
    ON DELETE SET NULL;

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_academic_year_id_fkey"
    FOREIGN KEY ("academic_year_id")
    REFERENCES "public"."academic_years" ("academic_year_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_semester_id_fkey"
    FOREIGN KEY ("semester_id")
    REFERENCES "public"."semesters" ("semester_id")
    ON DELETE RESTRICT;

-- ============================================================================
-- E. student_attendance
-- ============================================================================
-- Daily attendance records for a student in a specific section.

CREATE TABLE IF NOT EXISTS "public"."student_attendance" (
    "student_attendance_id"  uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id"             uuid  NOT NULL,
    "section_id"             uuid  NOT NULL,
    "academic_year_id"       uuid  NOT NULL,
    "semester_id"            uuid  NOT NULL,
    date                   date  NOT NULL,
    "status"                 text  NOT NULL,
    "notes"                  text,
    "created_at"             timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "student_attendance_status_check"
        CHECK (("status" = ANY (ARRAY[
            'present'::text,
            'absent'::text,
            'late'::text,
            'excused'::text
        ]))),
    CONSTRAINT "student_attendance_status_not_blank_check"
        CHECK (("btrim"("status") <> ''::text))
);

ALTER TABLE "public"."student_attendance" OWNER TO "postgres";

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_pkey" PRIMARY KEY ("student_attendance_id");

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_student_section_date_key"
    UNIQUE ("student_id", "section_id", date);

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_student_id_fkey"
    FOREIGN KEY ("student_id")
    REFERENCES "public"."students" ("student_id")
    ON DELETE CASCADE;

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_section_id_fkey"
    FOREIGN KEY ("section_id")
    REFERENCES "public"."sections" ("section_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_academic_year_id_fkey"
    FOREIGN KEY ("academic_year_id")
    REFERENCES "public"."academic_years" ("academic_year_id")
    ON DELETE RESTRICT;

ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_semester_id_fkey"
    FOREIGN KEY ("semester_id")
    REFERENCES "public"."semesters" ("semester_id")
    ON DELETE RESTRICT;

-- ============================================================================
-- F. faqs
-- ============================================================================
-- Frequently-asked-questions, either global or scoped to an institution.

CREATE TABLE IF NOT EXISTS "public"."faqs" (
    "faq_id"            uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id"    uuid,
    "category"          text  DEFAULT 'general'::text NOT NULL,
    "question"          text  NOT NULL,
    "answer"            text  NOT NULL,
    "display_order"     integer DEFAULT 0 NOT NULL,
    "is_active"         boolean DEFAULT true NOT NULL,
    "created_at"        timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"        timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "faqs_question_not_blank_check"
        CHECK (("btrim"("question") <> ''::text)),
    CONSTRAINT "faqs_answer_not_blank_check"
        CHECK (("btrim"("answer") <> ''::text)),
    CONSTRAINT "faqs_display_order_check"
        CHECK (("display_order" >= 0))
);

ALTER TABLE "public"."faqs" OWNER TO "postgres";

ALTER TABLE ONLY "public"."faqs"
    ADD CONSTRAINT "faqs_pkey" PRIMARY KEY ("faq_id");

ALTER TABLE ONLY "public"."faqs"
    ADD CONSTRAINT "faqs_institution_id_fkey"
    FOREIGN KEY ("institution_id")
    REFERENCES "public"."institutions" ("institution_id")
    ON DELETE SET NULL;

-- ============================================================================
-- G. notices
-- ============================================================================
-- Notice / announcement board entries.

CREATE TABLE IF NOT EXISTS "public"."notices" (
    "notice_id"          uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id"     uuid,
    "title"              text  NOT NULL,
    "content"            text  NOT NULL,
    "category"           text  DEFAULT 'general'::text NOT NULL,
    "priority"           text  DEFAULT 'normal'::text NOT NULL,
    "is_active"          boolean DEFAULT true NOT NULL,
    "is_pinned"          boolean DEFAULT false NOT NULL,
    "published_at"       timestamp with time zone,
    "expires_at"         timestamp with time zone,
    "created_by"         uuid,
    "created_at"         timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"         timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "notices_title_not_blank_check"
        CHECK (("btrim"("title") <> ''::text)),
    CONSTRAINT "notices_content_not_blank_check"
        CHECK (("btrim"("content") <> ''::text)),
    CONSTRAINT "notices_category_check"
        CHECK (("category" = ANY (ARRAY[
            'general'::text,
            'academic'::text,
            'event'::text,
            'holiday'::text,
            'exam'::text,
            'other'::text
        ]))),
    CONSTRAINT "notices_priority_check"
        CHECK (("priority" = ANY (ARRAY[
            'low'::text,
            'normal'::text,
            'high'::text,
            'urgent'::text
        ])))
);

ALTER TABLE "public"."notices" OWNER TO "postgres";

ALTER TABLE ONLY "public"."notices"
    ADD CONSTRAINT "notices_pkey" PRIMARY KEY ("notice_id");

ALTER TABLE ONLY "public"."notices"
    ADD CONSTRAINT "notices_institution_id_fkey"
    FOREIGN KEY ("institution_id")
    REFERENCES "public"."institutions" ("institution_id")
    ON DELETE SET NULL;

ALTER TABLE ONLY "public"."notices"
    ADD CONSTRAINT "notices_created_by_fkey"
    FOREIGN KEY ("created_by")
    REFERENCES "public"."users" ("user_id")
    ON DELETE SET NULL;

-- ============================================================================
-- H. admin_audit_log
-- ============================================================================
-- Audit trail of privileged admin actions (insert / update / delete on
-- protected tables, auth events, etc.).

CREATE TABLE IF NOT EXISTS "public"."admin_audit_log" (
    "audit_id"        uuid  DEFAULT "gen_random_uuid"() NOT NULL,
    "actor_user_id"   uuid  NOT NULL,
    "action"          text  NOT NULL,
    "table_name"      text,
    "record_id"       text,
    "record_data"     "jsonb",
    "ip_address"      "inet",
    "user_agent"      text,
    "status"          text  DEFAULT 'success'::text NOT NULL,
    "performed_at"    timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "admin_audit_log_action_not_blank_check"
        CHECK (("btrim"("action") <> ''::text)),
    CONSTRAINT "admin_audit_log_status_check"
        CHECK (("status" = ANY (ARRAY[
            'success'::text,
            'failure'::text,
            'info'::text
        ])))
);

ALTER TABLE "public"."admin_audit_log" OWNER TO "postgres";

ALTER TABLE ONLY "public"."admin_audit_log"
    ADD CONSTRAINT "admin_audit_log_pkey" PRIMARY KEY ("audit_id");

ALTER TABLE ONLY "public"."admin_audit_log"
    ADD CONSTRAINT "admin_audit_log_actor_user_id_fkey"
    FOREIGN KEY ("actor_user_id")
    REFERENCES "public"."users" ("user_id")
    ON DELETE RESTRICT;

-- ============================================================================
-- Indexes (performance on FK columns and common query patterns)
-- ============================================================================

-- students
CREATE INDEX IF NOT EXISTS "idx_students_user_id" ON "public"."students" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_students_institution_id" ON "public"."students" ("institution_id");
CREATE INDEX IF NOT EXISTS "idx_students_program_id" ON "public"."students" ("program_id");
CREATE INDEX IF NOT EXISTS "idx_students_academic_year_id" ON "public"."students" ("academic_year_id");
CREATE INDEX IF NOT EXISTS "idx_students_is_active" ON "public"."students" ("is_active");

-- student_results
CREATE INDEX IF NOT EXISTS "idx_student_results_student_id" ON "public"."student_results" ("student_id");
CREATE INDEX IF NOT EXISTS "idx_student_results_ay_semester" ON "public"."student_results" ("academic_year_id", "semester_id");
CREATE INDEX IF NOT EXISTS "idx_student_results_program_id" ON "public"."student_results" ("program_id");

-- student_result_items
CREATE INDEX IF NOT EXISTS "idx_student_result_items_result_id" ON "public"."student_result_items" ("student_result_id");
CREATE INDEX IF NOT EXISTS "idx_student_result_items_course_id" ON "public"."student_result_items" ("course_id");
CREATE INDEX IF NOT EXISTS "idx_student_result_items_section_id" ON "public"."student_result_items" ("section_id");

-- test_results
CREATE INDEX IF NOT EXISTS "idx_test_results_student_id" ON "public"."test_results" ("student_id");
CREATE INDEX IF NOT EXISTS "idx_test_results_course_id" ON "public"."test_results" ("course_id");
CREATE INDEX IF NOT EXISTS "idx_test_results_section_id" ON "public"."test_results" ("section_id");
CREATE INDEX IF NOT EXISTS "idx_test_results_ay_semester" ON "public"."test_results" ("academic_year_id", "semester_id");

-- student_attendance
CREATE INDEX IF NOT EXISTS "idx_student_attendance_student_id" ON "public"."student_attendance" ("student_id");
CREATE INDEX IF NOT EXISTS "idx_student_attendance_section_id" ON "public"."student_attendance" ("section_id");
CREATE INDEX IF NOT EXISTS "idx_student_attendance_date" ON "public"."student_attendance" (date);

-- faqs
CREATE INDEX IF NOT EXISTS "idx_faqs_institution_id" ON "public"."faqs" ("institution_id");
CREATE INDEX IF NOT EXISTS "idx_faqs_category" ON "public"."faqs" ("category");
CREATE INDEX IF NOT EXISTS "idx_faqs_is_active" ON "public"."faqs" ("is_active");

-- notices
CREATE INDEX IF NOT EXISTS "idx_notices_institution_id" ON "public"."notices" ("institution_id");
CREATE INDEX IF NOT EXISTS "idx_notices_category" ON "public"."notices" ("category");
CREATE INDEX IF NOT EXISTS "idx_notices_priority" ON "public"."notices" ("priority");
CREATE INDEX IF NOT EXISTS "idx_notices_published_at" ON "public"."notices" ("published_at");
CREATE INDEX IF NOT EXISTS "idx_notices_is_pinned" ON "public"."notices" ("is_pinned");
CREATE INDEX IF NOT EXISTS "idx_notices_is_active" ON "public"."notices" ("is_active");

-- admin_audit_log
CREATE INDEX IF NOT EXISTS "idx_admin_audit_log_actor_user_id" ON "public"."admin_audit_log" ("actor_user_id");
CREATE INDEX IF NOT EXISTS "idx_admin_audit_log_action" ON "public"."admin_audit_log" ("action");
CREATE INDEX IF NOT EXISTS "idx_admin_audit_log_performed_at" ON "public"."admin_audit_log" ("performed_at");
CREATE INDEX IF NOT EXISTS "idx_admin_audit_log_status" ON "public"."admin_audit_log" ("status");

-- ============================================================================
-- Service role grants
-- ============================================================================

GRANT ALL ON TABLE
    "public"."students",
    "public"."student_results",
    "public"."student_result_items",
    "public"."test_results",
    "public"."student_attendance",
    "public"."faqs",
    "public"."notices",
    "public"."admin_audit_log"
TO "service_role";

-- ============================================================================
-- Table-level comments
-- ============================================================================

COMMENT ON TABLE "public"."students" IS 'Student academic profile linked one-to-one to public.users';
COMMENT ON TABLE "public"."student_results" IS 'Consolidated per-semester result summary';
COMMENT ON TABLE "public"."student_result_items" IS 'Individual course-grade rows within a student_result';
COMMENT ON TABLE "public"."test_results" IS 'Per-test / per-exam scores for a student';
COMMENT ON TABLE "public"."student_attendance" IS 'Daily attendance records per student-section';
COMMENT ON TABLE "public"."faqs" IS 'Frequently-asked-questions (global or per-institution)';
COMMENT ON TABLE "public"."notices" IS 'Notice / announcement board entries';
COMMENT ON TABLE "public"."admin_audit_log" IS 'Audit trail of privileged admin actions';

-- ============================================================================
-- I. Seed data
-- ============================================================================

-- ----------------------------------------------------------------------------
-- I-A. auth.users (DEMO ACCOUNTS — provisioned via Supabase Auth Admin API)
-- ----------------------------------------------------------------------------
-- NOTE (ADMIN-5 defect fix): earlier drafts seeded auth.users with raw SQL
-- INSERTs. GoTrue does NOT recognise such rows (the Auth API filters by
-- instance/identity state that raw inserts cannot reproduce), so OTP/magic-link
-- login for those accounts failed with "Database error finding user".
-- The supported mechanism is the GoTrue Admin API (supabase_auth):
--     admin.auth.admin.create_user({"email": ..., "password": ..., "email_confirm": True})
-- and then linking public.users.auth_user_id to the generated auth user id.
-- The demo profiles (public.users / user_roles / students) below are seeded
-- with placeholder auth_user_id values that provisioning must overwrite.

-- ----------------------------------------------------------------------------
-- I-B. public.users
-- The existing Demo Student (user_id ...0101) and Demo Faculty
-- (user_id 8464c7b9-...) already have rows. Only new users are inserted.
-- ----------------------------------------------------------------------------

INSERT INTO "public"."users" AS "u" (
    "user_id",
    "auth_user_id",
    "email",
    "first_name",
    "last_name",
    "display_name",
    "status"
) VALUES
(
    '30000000-0000-0000-0000-000000000102',
    '40000000-0000-0000-0000-000000000001',
    'admin.demo@collegeai.local',
    'Demo',
    'Admin',
    'Demo Admin',
    'active'
),
(
    '30000000-0000-0000-0000-000000000103',
    '40000000-0000-0000-0000-000000000002',
    'student2.demo@collegeai.local',
    'Jane',
    'Doe',
    'Jane Doe',
    'active'
),
(
    '30000000-0000-0000-0000-000000000104',
    '40000000-0000-0000-0000-000000000003',
    'student3.demo@collegeai.local',
    'Alice',
    'Smith',
        'Alice Smith',
    'active'
)
ON CONFLICT ("user_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-C. user_roles
-- Existing assignments: Demo Student (...0101 -> student) and Demo Faculty
-- (8464c7b9... -> faculty) already exist. Only new assignments inserted.
-- ----------------------------------------------------------------------------

INSERT INTO "public"."user_roles" AS "ur" (
    "user_id",
    "role_id"
) VALUES
(
    '30000000-0000-0000-0000-000000000102',  -- Demo Admin
    '10000000-0000-0000-0000-000000000001'   -- admin
),
(
    '30000000-0000-0000-0000-000000000103',  -- Jane Doe
    '10000000-0000-0000-0000-000000000003'   -- student
),
(
    '30000000-0000-0000-0000-000000000104',  -- Alice Smith
    '10000000-0000-0000-0000-000000000003'   -- student
)
ON CONFLICT ("user_id", "role_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-D. students (student profiles)
-- student_id values are explicitly set using the 50000000 convention-range so
-- that downstream FK inserts can reference them deterministically.
-- ----------------------------------------------------------------------------

INSERT INTO "public"."students" AS "s" (
    "student_id",
    "user_id",
    "institution_id",
    "student_number",
    "program_id",
    "academic_year_id",
    "enrollment_date",
    "expected_graduation_date"
) VALUES
(
    '30000000-0000-0000-0000-000000000151',  -- Student 1 (Demo Student)
    '30000000-0000-0000-0000-000000000101',
    '30000000-0000-0000-0000-000000000001',  -- GIT institution
    'STU2026001',
    '30000000-0000-0000-0000-000000000042',  -- BT-AIDS
    '30000000-0000-0000-0000-000000000022',  -- 2026-2027
    '2026-07-01',
    '2030-06-30'
),
(
    '30000000-0000-0000-0000-000000000152',  -- Student 2 (Jane Doe)
    '30000000-0000-0000-0000-000000000103',
    '30000000-0000-0000-0000-000000000001',
    'STU2026002',
    '30000000-0000-0000-0000-000000000042',
    '30000000-0000-0000-0000-000000000022',
    '2026-07-01',
    '2030-06-30'
),
(
    '30000000-0000-0000-0000-000000000153',  -- Student 3 (Alice Smith)
    '30000000-0000-0000-0000-000000000104',
    '30000000-0000-0000-0000-000000000001',
    'STU2026003',
    '30000000-0000-0000-0000-000000000042',
    '30000000-0000-0000-0000-000000000022',
    '2026-07-01',
        '2030-06-30'
)
ON CONFLICT ("student_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-E. student_results (semester result summaries)
-- All three students are in BT-AIDS, AY 2026-2027, Semester 3.
-- ----------------------------------------------------------------------------

INSERT INTO "public"."student_results" AS "sr" (
    "student_result_id",
    "student_id",
    "academic_year_id",
    "semester_id",
    "program_id",
    "result_type",
    "total_credits_earned",
    "total_credits_max",
    "sgpa",
    "cgpa",
    "status",
    "issued_at"
) VALUES
(
    '30000000-0000-0000-0000-000000000201',  -- Result 1 (Student 1)
    '30000000-0000-0000-0000-000000000151',  -- Student 1
    '30000000-0000-0000-0000-000000000022',  -- AY 2026-2027
    '30000000-0000-0000-0000-000000000033',  -- SEM3
    '30000000-0000-0000-0000-000000000042',  -- BT-AIDS
    'semester',
    8.00,
    8.00,
    8.50,
    8.75,
    'published',
    '2026-09-09T00:00:00+00:00'
),
(
    '30000000-0000-0000-0000-000000000202',  -- Result 2 (Student 2)
    '30000000-0000-0000-0000-000000000152',  -- Student 2
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '30000000-0000-0000-0000-000000000042',
    'semester',
    8.00,
    8.00,
    7.50,
    7.85,
    'published',
    '2026-09-09T00:00:00+00:00'
),
(
    '30000000-0000-0000-0000-000000000203',  -- Result 3 (Student 3)
    '30000000-0000-0000-0000-000000000153',  -- Student 3
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '30000000-0000-0000-0000-000000000042',
    'semester',
    8.00,
    8.00,
    9.50,
    9.20,
    'published',
    '2026-09-09T00:00:00+00:00'
)
ON CONFLICT ("student_result_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-F. student_result_items (individual course grades)
-- Courses: CS101 (...051, section ...099) and AI301 (...054, section ...094)
-- ----------------------------------------------------------------------------

INSERT INTO "public"."student_result_items" AS "sri" (
    "student_result_item_id",
    "student_result_id",
    "course_id",
    "section_id",
    "credits_earned",
    "credits_max",
    "grade_points",
    "letter_grade",
    "grade_value"
) VALUES
(
    '30000000-0000-0000-0000-000000000301',  -- Item 1 (Result 1, CS101)
    '30000000-0000-0000-0000-000000000201',
    '30000000-0000-0000-0000-000000000051',  -- CS101
    '30000000-0000-0000-0000-000000000099',  -- Section AIDS-CS101-A
    4.00, 4.00, 9.00, 'A',  9.00
),
(
    '30000000-0000-0000-0000-000000000302',  -- Item 2 (Result 1, AI301)
    '30000000-0000-0000-0000-000000000201',
    '30000000-0000-0000-0000-000000000054',  -- AI301
    '30000000-0000-0000-0000-000000000094',  -- Section AIDS-AI301-A
    4.00, 4.00, 8.00, 'B+', 8.00
),
(
    '30000000-0000-0000-0000-000000000303',  -- Item 3 (Result 2, CS101)
    '30000000-0000-0000-0000-000000000202',
    '30000000-0000-0000-0000-000000000051',
    '30000000-0000-0000-0000-000000000099',
    4.00, 4.00, 7.00, 'B',  7.00
),
(
    '30000000-0000-0000-0000-000000000304',  -- Item 4 (Result 2, AI301)
    '30000000-0000-0000-0000-000000000202',
    '30000000-0000-0000-0000-000000000054',
    '30000000-0000-0000-0000-000000000094',
    4.00, 4.00, 8.00, 'B+', 8.00
),
(
    '30000000-0000-0000-0000-000000000305',  -- Item 5 (Result 3, CS101)
    '30000000-0000-0000-0000-000000000203',
    '30000000-0000-0000-0000-000000000051',
    '30000000-0000-0000-0000-000000000099',
    4.00, 4.00, 10.00,'A+', 10.00
),
(
    '30000000-0000-0000-0000-000000000306',  -- Item 6 (Result 3, AI301)
    '30000000-0000-0000-0000-000000000203',
    '30000000-0000-0000-0000-000000000054',
    '30000000-0000-0000-0000-000000000094',
    4.00, 4.00, 9.00, 'A',  9.00
)
ON CONFLICT ("student_result_item_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-G. test_results (test and exam scores)
-- ----------------------------------------------------------------------------

INSERT INTO "public"."test_results" AS "tr" (
    "test_result_id",
    "student_id",
    "course_id",
    "section_id",
    "academic_year_id",
    "semester_id",
    "test_name",
    "test_type",
    "max_marks",
    "scored_marks",
    "percentage",
    "letter_grade",
    "conducted_at",
    "status"
) VALUES
(
    '30000000-0000-0000-0000-000000000401',
    '30000000-0000-0000-0000-000000000151',
    '30000000-0000-0000-0000-000000000051',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    'Midterm Examination',
    'midterm',
    100.00,
    88.00,
    88.00,
    'A',
    '2026-09-02T09:00:00+00:00',
    'published'
),
(
    '30000000-0000-0000-0000-000000000402',
    '30000000-0000-0000-0000-000000000152',
    '30000000-0000-0000-0000-000000000051',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    'Midterm Examination',
    'midterm',
    100.00,
    76.00,
    76.00,
    'B',
    '2026-09-02T09:00:00+00:00',
    'published'
),
(
    '30000000-0000-0000-0000-000000000403',
    '30000000-0000-0000-0000-000000000153',
    '30000000-0000-0000-0000-000000000051',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    'Midterm Examination',
    'midterm',
    100.00,
    94.00,
    94.00,
    'A+',
    '2026-09-02T09:00:00+00:00',
    'published'
),
(
    '30000000-0000-0000-0000-000000000404',
    '30000000-0000-0000-0000-000000000151',
    '30000000-0000-0000-0000-000000000054',
    '30000000-0000-0000-0000-000000000094',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    'Quiz 1',
    'quiz',
    20.00,
    18.00,
    90.00,
    'A',
    '2026-08-20T09:00:00+00:00',
    'published'
),
(
    '30000000-0000-0000-0000-000000000405',
    '30000000-0000-0000-0000-000000000152',
    '30000000-0000-0000-0000-000000000054',
    '30000000-0000-0000-0000-000000000094',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    'Quiz 1',
    'quiz',
    20.00,
    16.00,
    80.00,
    'B+',
    '2026-08-20T09:00:00+00:00',
    'published'
),
(
    '30000000-0000-0000-0000-000000000406',
    '30000000-0000-0000-0000-000000000153',
    '30000000-0000-0000-0000-000000000054',
    '30000000-0000-0000-0000-000000000094',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    'Quiz 1',
    'quiz',
    20.00,
    19.00,
    95.00,
    'A+',
    '2026-08-20T09:00:00+00:00',
    'published'
)
ON CONFLICT ("test_result_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-H. student_attendance (daily attendance)
-- ----------------------------------------------------------------------------

INSERT INTO "public"."student_attendance" AS "sa" (
    "student_attendance_id",
    "student_id",
    "section_id",
    "academic_year_id",
    "semester_id",
    date,
    "status",
    "notes"
) VALUES
(
    '30000000-0000-0000-0000-000000000501',
    '30000000-0000-0000-0000-000000000151',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '2026-08-17',
    'present',
    NULL
),
(
    '30000000-0000-0000-0000-000000000502',
    '30000000-0000-0000-0000-000000000151',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '2026-08-18',
    'late',
    'Arrived after the first period.'
),
(
    '30000000-0000-0000-0000-000000000503',
    '30000000-0000-0000-0000-000000000152',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '2026-08-17',
    'present',
    NULL
),
(
    '30000000-0000-0000-0000-000000000504',
    '30000000-0000-0000-0000-000000000152',
    '30000000-0000-0000-0000-000000000099',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '2026-08-18',
    'absent',
    'Medical leave submitted.'
),
(
    '30000000-0000-0000-0000-000000000505',
    '30000000-0000-0000-0000-000000000153',
    '30000000-0000-0000-0000-000000000094',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '2026-08-17',
    'present',
    NULL
),
(
    '30000000-0000-0000-0000-000000000506',
    '30000000-0000-0000-0000-000000000153',
    '30000000-0000-0000-0000-000000000094',
    '30000000-0000-0000-0000-000000000022',
    '30000000-0000-0000-0000-000000000033',
    '2026-08-18',
    'excused',
    'Represented the institution at an academic event.'
)
ON CONFLICT ("student_attendance_id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- I-I. FAQs, notices, and the initial admin audit entry
-- ----------------------------------------------------------------------------

INSERT INTO "public"."faqs" AS "f" (
    "faq_id",
    "institution_id",
    "category",
    "question",
    "answer",
    "display_order",
    "is_active"
) VALUES
(
    '30000000-0000-0000-0000-000000000601',
    '30000000-0000-0000-0000-000000000001',
    'academic',
    'Where can students view their semester results?',
    'Open My Academics after signing in to view published semester results.',
    1,
    true
),
(
    '30000000-0000-0000-0000-000000000602',
    NULL,
    'general',
    'How do students contact the academic office?',
    'Use the contact details published in the latest institutional notice.',
    2,
    true
)
ON CONFLICT ("faq_id") DO NOTHING;

INSERT INTO "public"."notices" AS "n" (
    "notice_id",
    "institution_id",
    "title",
    "content",
    "category",
    "priority",
    "is_active",
    "is_pinned",
    "published_at",
    "created_by"
) VALUES
(
    '30000000-0000-0000-0000-000000000701',
    '30000000-0000-0000-0000-000000000001',
    'Midterm results published',
    'Midterm results for the current semester are available in My Academics.',
    'exam',
    'high',
    true,
    true,
    '2026-09-09T00:00:00+00:00',
    '30000000-0000-0000-0000-000000000102'
),
(
    '30000000-0000-0000-0000-000000000702',
    '30000000-0000-0000-0000-000000000001',
    'Attendance review window',
    'Students may contact the academic office to request an attendance correction.',
    'academic',
    'normal',
    true,
    false,
    '2026-09-09T00:00:00+00:00',
    '30000000-0000-0000-0000-000000000102'
)
ON CONFLICT ("notice_id") DO NOTHING;

INSERT INTO "public"."admin_audit_log" AS "al" (
    "audit_id",
    "actor_user_id",
    "action",
    "table_name",
    "record_id",
    "record_data",
    "status",
    "performed_at"
) VALUES (
    '30000000-0000-0000-0000-000000000801',
    '30000000-0000-0000-0000-000000000102',
    'admin_1_seed',
    'admin_audit_log',
    '30000000-0000-0000-0000-000000000801',
    '{"migration":"20260909000000_phase_admin_1_admin_student_schema.sql","seeded_tables":8}'::jsonb,
    'success',
    '2026-09-09T00:00:00+00:00'
)
ON CONFLICT ("audit_id") DO NOTHING;




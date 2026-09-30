-- ============================================================================
-- Phase Admin-1 - Database Foundation (Admin & Student Academic Schema)
-- ============================================================================
--
-- Creates eight new tables that support the Admin module and the authenticated
-- student "My Academics" endpoints:
--
--   1. students              - Student profile, linked one-to-one to users.id
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
--   * FK references use the authoritative committed schema contract:
--     child user_id columns reference public.users.id.
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
    REFERENCES "public"."users" ("id")
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
    REFERENCES "public"."users" ("id")
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
    REFERENCES "public"."users" ("id")
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
-- Demo provisioning boundary
-- ============================================================================
--
-- Historical drafts embedded a connected demo snapshot here (public users,
-- roles, students, results, attendance, FAQs, notices, and an audit row).
-- Those rows depended on pre-existing deployment data and placeholder
-- auth_user_id values that were not valid auth.users identities on a fresh
-- database. Demo identities and their dependent data are therefore not
-- structural migration data. Local identities must be created after migrations
-- through the supported local GoTrue Admin API and then linked to public.users.
-- The authoritative users_auth_user_id_fkey remains enforced.




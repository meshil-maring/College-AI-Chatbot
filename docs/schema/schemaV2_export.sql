


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."academic_years" (
    "academic_year_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "start_date" "date" NOT NULL,
    "end_date" "date" NOT NULL,
    "is_current" boolean DEFAULT false NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "academic_years_code_check" CHECK (("length"(TRIM(BOTH FROM "code")) > 0)),
    CONSTRAINT "academic_years_date_check" CHECK (("end_date" > "start_date")),
    CONSTRAINT "academic_years_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0))
);


ALTER TABLE "public"."academic_years" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."ai_responses" (
    "ai_response_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "message_id" "uuid" NOT NULL,
    "provider_name" "text" NOT NULL,
    "model_name" "text" NOT NULL,
    "validation_status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "input_token_count" integer,
    "output_token_count" integer,
    "latency_ms" integer,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "ai_responses_input_token_count_check" CHECK ((("input_token_count" IS NULL) OR ("input_token_count" >= 0))),
    CONSTRAINT "ai_responses_latency_ms_check" CHECK ((("latency_ms" IS NULL) OR ("latency_ms" >= 0))),
    CONSTRAINT "ai_responses_model_name_check" CHECK (("length"("btrim"("model_name")) > 0)),
    CONSTRAINT "ai_responses_output_token_count_check" CHECK ((("output_token_count" IS NULL) OR ("output_token_count" >= 0))),
    CONSTRAINT "ai_responses_provider_name_check" CHECK (("length"("btrim"("provider_name")) > 0)),
    CONSTRAINT "ai_responses_validation_status_check" CHECK (("validation_status" = ANY (ARRAY['pending'::"text", 'passed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."ai_responses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."campuses" (
    "campus_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "description" "text",
    "address" "text",
    "city" "text",
    "state" "text",
    "country" "text",
    "postal_code" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."campuses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversations" (
    "conversation_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "title" "text",
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "conversations_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'archived'::"text"])))
);


ALTER TABLE "public"."conversations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."course_offerings" (
    "course_offering_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "course_id" "uuid" NOT NULL,
    "academic_year_id" "uuid" NOT NULL,
    "semester_id" "uuid" NOT NULL,
    "program_id" "uuid" NOT NULL,
    "capacity" integer,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "course_offerings_capacity_check" CHECK ((("capacity" IS NULL) OR ("capacity" > 0)))
);


ALTER TABLE "public"."course_offerings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."courses" (
    "course_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "department_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "description" "text",
    "credits" numeric(5,2),
    "lecture_hours" numeric(5,2),
    "tutorial_hours" numeric(5,2),
    "practical_hours" numeric(5,2),
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "courses_code_check" CHECK (("length"(TRIM(BOTH FROM "code")) > 0)),
    CONSTRAINT "courses_credits_check" CHECK ((("credits" IS NULL) OR ("credits" > (0)::numeric))),
    CONSTRAINT "courses_lecture_hours_check" CHECK ((("lecture_hours" IS NULL) OR ("lecture_hours" >= (0)::numeric))),
    CONSTRAINT "courses_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0)),
    CONSTRAINT "courses_practical_hours_check" CHECK ((("practical_hours" IS NULL) OR ("practical_hours" >= (0)::numeric))),
    CONSTRAINT "courses_tutorial_hours_check" CHECK ((("tutorial_hours" IS NULL) OR ("tutorial_hours" >= (0)::numeric)))
);


ALTER TABLE "public"."courses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."departments" (
    "department_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "campus_id" "uuid",
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "description" "text",
    "email" "text",
    "phone" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."departments" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_processing_runs" (
    "processing_run_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_version_id" "uuid" NOT NULL,
    "status" "text" DEFAULT 'queued'::"text" NOT NULL,
    "processor_name" "text",
    "processor_version" "text",
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "document_processing_runs_failed_error_check" CHECK ((("status" <> 'failed'::"text") OR ("error_message" IS NOT NULL))),
    CONSTRAINT "document_processing_runs_status_check" CHECK (("status" = ANY (ARRAY['queued'::"text", 'processing'::"text", 'ready'::"text", 'failed'::"text"]))),
    CONSTRAINT "document_processing_runs_time_check" CHECK ((("completed_at" IS NULL) OR ("started_at" IS NULL) OR ("completed_at" >= "started_at")))
);


ALTER TABLE "public"."document_processing_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_versions" (
    "document_version_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_id" "uuid" NOT NULL,
    "version_number" integer NOT NULL,
    "version_label" "text",
    "original_filename" "text" NOT NULL,
    "file_type" "text" NOT NULL,
    "mime_type" "text",
    "file_size_bytes" bigint,
    "storage_provider" "text" NOT NULL,
    "storage_bucket" "text" NOT NULL,
    "storage_object_key" "text" NOT NULL,
    "file_checksum" "text",
    "lifecycle_status" "text" DEFAULT 'draft'::"text" NOT NULL,
    "effective_from" "date",
    "effective_until" "date",
    "supersedes_version_id" "uuid",
    "created_by_user_id" "uuid" NOT NULL,
    "reviewed_by_user_id" "uuid",
    "approved_by_user_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "document_versions_effective_dates_check" CHECK ((("effective_until" IS NULL) OR ("effective_from" IS NULL) OR ("effective_until" >= "effective_from"))),
    CONSTRAINT "document_versions_file_size_check" CHECK ((("file_size_bytes" IS NULL) OR ("file_size_bytes" >= 0))),
    CONSTRAINT "document_versions_file_type_check" CHECK (("btrim"("file_type") <> ''::"text")),
    CONSTRAINT "document_versions_lifecycle_status_check" CHECK (("lifecycle_status" = ANY (ARRAY['draft'::"text", 'under_review'::"text", 'approved'::"text", 'published'::"text", 'archived'::"text", 'superseded'::"text"]))),
    CONSTRAINT "document_versions_storage_bucket_check" CHECK (("btrim"("storage_bucket") <> ''::"text")),
    CONSTRAINT "document_versions_storage_object_key_check" CHECK (("btrim"("storage_object_key") <> ''::"text")),
    CONSTRAINT "document_versions_storage_provider_check" CHECK (("btrim"("storage_provider") <> ''::"text")),
    CONSTRAINT "document_versions_version_number_check" CHECK (("version_number" > 0))
);


ALTER TABLE "public"."document_versions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."documents" (
    "document_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "knowledge_source_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."institutions" (
    "institution_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "description" "text",
    "website_url" "text",
    "email" "text",
    "phone" "text",
    "address" "text",
    "city" "text",
    "state" "text",
    "country" "text",
    "postal_code" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."institutions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_chunks" (
    "chunk_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "processing_run_id" "uuid" NOT NULL,
    "chunk_sequence" integer NOT NULL,
    "content_text" "text" NOT NULL,
    "page_start" integer,
    "page_end" integer,
    "section_title" "text",
    "source_locator" "text",
    "token_count" integer,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "knowledge_chunks_content_check" CHECK (("btrim"("content_text") <> ''::"text")),
    CONSTRAINT "knowledge_chunks_page_end_check" CHECK ((("page_end" IS NULL) OR ("page_end" > 0))),
    CONSTRAINT "knowledge_chunks_page_range_check" CHECK ((("page_end" IS NULL) OR ("page_start" IS NULL) OR ("page_end" >= "page_start"))),
    CONSTRAINT "knowledge_chunks_page_start_check" CHECK ((("page_start" IS NULL) OR ("page_start" > 0))),
    CONSTRAINT "knowledge_chunks_sequence_check" CHECK (("chunk_sequence" > 0)),
    CONSTRAINT "knowledge_chunks_token_count_check" CHECK ((("token_count" IS NULL) OR ("token_count" >= 0)))
);


ALTER TABLE "public"."knowledge_chunks" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_sources" (
    "knowledge_source_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "source_type" "text" NOT NULL,
    "title" "text" NOT NULL,
    "description" "text",
    "owner_user_id" "uuid",
    "created_by_user_id" "uuid" NOT NULL,
    "reviewed_by_user_id" "uuid",
    "approved_by_user_id" "uuid",
    "authority_level" "text" DEFAULT 'standard'::"text" NOT NULL,
    "lifecycle_status" "text" DEFAULT 'draft'::"text" NOT NULL,
    "effective_from" "date",
    "effective_until" "date",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "knowledge_sources_authority_level_check" CHECK (("btrim"("authority_level") <> ''::"text")),
    CONSTRAINT "knowledge_sources_effective_dates_check" CHECK ((("effective_until" IS NULL) OR ("effective_from" IS NULL) OR ("effective_until" >= "effective_from"))),
    CONSTRAINT "knowledge_sources_lifecycle_status_check" CHECK (("lifecycle_status" = ANY (ARRAY['draft'::"text", 'under_review'::"text", 'approved'::"text", 'published'::"text", 'archived'::"text", 'superseded'::"text"]))),
    CONSTRAINT "knowledge_sources_source_type_check" CHECK (("btrim"("source_type") <> ''::"text"))
);


ALTER TABLE "public"."knowledge_sources" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."message_citations" (
    "message_citation_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "message_id" "uuid" NOT NULL,
    "retrieval_operation_id" "uuid" NOT NULL,
    "chunk_id" "uuid" NOT NULL,
    "display_order" integer NOT NULL,
    "citation_label" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "message_citations_display_order_check" CHECK (("display_order" > 0))
);


ALTER TABLE "public"."message_citations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."messages" (
    "message_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "conversation_id" "uuid" NOT NULL,
    "message_sequence" integer NOT NULL,
    "message_type" "text" NOT NULL,
    "content_text" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "messages_content_check" CHECK (("length"("btrim"("content_text")) > 0)),
    CONSTRAINT "messages_sequence_check" CHECK (("message_sequence" > 0)),
    CONSTRAINT "messages_type_check" CHECK (("message_type" = ANY (ARRAY['user'::"text", 'assistant'::"text"])))
);


ALTER TABLE "public"."messages" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."permissions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "code" "text" NOT NULL,
    "scope" "text" DEFAULT 'global'::character varying NOT NULL,
    CONSTRAINT "permissions_scope_check" CHECK (("btrim"("scope") <> ''::"text"))
);


ALTER TABLE "public"."permissions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."program_courses" (
    "program_course_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "program_id" "uuid" NOT NULL,
    "course_id" "uuid" NOT NULL,
    "semester_id" "uuid",
    "course_type" "text" NOT NULL,
    "is_required" boolean DEFAULT true NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "program_courses_course_type_check" CHECK (("course_type" = ANY (ARRAY['core'::"text", 'elective'::"text", 'open_elective'::"text", 'skill'::"text", 'project'::"text"])))
);


ALTER TABLE "public"."program_courses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."programs" (
    "program_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "department_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "degree_type" "text" NOT NULL,
    "description" "text",
    "duration_years" numeric(4,2) NOT NULL,
    "total_credits" numeric(6,2),
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "programs_duration_years_check" CHECK (("duration_years" > (0)::numeric))
);


ALTER TABLE "public"."programs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."retrieval_operations" (
    "retrieval_operation_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "ai_response_id" "uuid" NOT NULL,
    "query_text" "text" NOT NULL,
    "status" "text" DEFAULT 'queued'::"text" NOT NULL,
    "result_count" integer,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    CONSTRAINT "retrieval_operations_query_text_check" CHECK (("length"("btrim"("query_text")) > 0)),
    CONSTRAINT "retrieval_operations_result_count_check" CHECK ((("result_count" IS NULL) OR ("result_count" >= 0))),
    CONSTRAINT "retrieval_operations_status_check" CHECK (("status" = ANY (ARRAY['queued'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"]))),
    CONSTRAINT "retrieval_operations_time_check" CHECK ((("completed_at" IS NULL) OR ("completed_at" >= "created_at")))
);


ALTER TABLE "public"."retrieval_operations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."retrieved_chunks" (
    "retrieval_operation_id" "uuid" NOT NULL,
    "chunk_id" "uuid" NOT NULL,
    "retrieval_rank" integer NOT NULL,
    "relevance_score" numeric,
    "selected_for_context" boolean DEFAULT false NOT NULL,
    CONSTRAINT "retrieved_chunks_retrieval_rank_check" CHECK (("retrieval_rank" > 0))
);


ALTER TABLE "public"."retrieved_chunks" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."role_permissions" (
    "role_id" "uuid" NOT NULL,
    "permission_id" "uuid" NOT NULL,
    "assigned_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."role_permissions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."roles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."roles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."sections" (
    "section_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "course_offering_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "capacity" integer,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "sections_capacity_check" CHECK ((("capacity" IS NULL) OR ("capacity" > 0))),
    CONSTRAINT "sections_code_check" CHECK (("length"(TRIM(BOTH FROM "code")) > 0)),
    CONSTRAINT "sections_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0))
);


ALTER TABLE "public"."sections" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."semesters" (
    "semester_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "academic_year_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "semester_number" integer NOT NULL,
    "start_date" "date" NOT NULL,
    "end_date" "date" NOT NULL,
    "is_current" boolean DEFAULT false NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "semesters_code_check" CHECK (("length"(TRIM(BOTH FROM "code")) > 0)),
    CONSTRAINT "semesters_date_check" CHECK (("end_date" > "start_date")),
    CONSTRAINT "semesters_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0)),
    CONSTRAINT "semesters_number_check" CHECK (("semester_number" > 0))
);


ALTER TABLE "public"."semesters" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_roles" (
    "user_id" "uuid" NOT NULL,
    "role_id" "uuid" NOT NULL,
    "assigned_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."user_roles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "auth_user_id" "uuid" NOT NULL,
    "email" "text" NOT NULL,
    "first_name" "text" NOT NULL,
    "last_name" "text" NOT NULL,
    "display_name" "text",
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_login_at" timestamp with time zone,
    CONSTRAINT "users_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'inactive'::"text", 'deactivated'::"text"])))
);


ALTER TABLE "public"."users" OWNER TO "postgres";


ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_institution_id_code_key" UNIQUE ("institution_id", "code");



ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_pkey" PRIMARY KEY ("academic_year_id");



ALTER TABLE ONLY "public"."ai_responses"
    ADD CONSTRAINT "ai_responses_message_id_key" UNIQUE ("message_id");



ALTER TABLE ONLY "public"."ai_responses"
    ADD CONSTRAINT "ai_responses_pkey" PRIMARY KEY ("ai_response_id");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_institution_id_campus_id_key" UNIQUE ("institution_id", "campus_id");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_institution_id_code_key" UNIQUE ("institution_id", "code");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_pkey" PRIMARY KEY ("campus_id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_pkey" PRIMARY KEY ("conversation_id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_course_program_year_semester_key" UNIQUE ("course_id", "program_id", "academic_year_id", "semester_id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_pkey" PRIMARY KEY ("course_offering_id");



ALTER TABLE ONLY "public"."courses"
    ADD CONSTRAINT "courses_department_id_code_key" UNIQUE ("department_id", "code");



ALTER TABLE ONLY "public"."courses"
    ADD CONSTRAINT "courses_pkey" PRIMARY KEY ("course_id");



ALTER TABLE ONLY "public"."departments"
    ADD CONSTRAINT "departments_institution_id_code_key" UNIQUE ("institution_id", "code");



ALTER TABLE ONLY "public"."departments"
    ADD CONSTRAINT "departments_pkey" PRIMARY KEY ("department_id");



ALTER TABLE ONLY "public"."document_processing_runs"
    ADD CONSTRAINT "document_processing_runs_pkey" PRIMARY KEY ("processing_run_id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_document_id_version_number_key" UNIQUE ("document_id", "version_number");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_pkey" PRIMARY KEY ("document_version_id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("document_id");



ALTER TABLE ONLY "public"."institutions"
    ADD CONSTRAINT "institutions_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."institutions"
    ADD CONSTRAINT "institutions_pkey" PRIMARY KEY ("institution_id");



ALTER TABLE ONLY "public"."knowledge_chunks"
    ADD CONSTRAINT "knowledge_chunks_pkey" PRIMARY KEY ("chunk_id");



ALTER TABLE ONLY "public"."knowledge_chunks"
    ADD CONSTRAINT "knowledge_chunks_processing_run_id_chunk_sequence_key" UNIQUE ("processing_run_id", "chunk_sequence");



ALTER TABLE ONLY "public"."knowledge_sources"
    ADD CONSTRAINT "knowledge_sources_pkey" PRIMARY KEY ("knowledge_source_id");



ALTER TABLE ONLY "public"."message_citations"
    ADD CONSTRAINT "message_citations_message_id_display_order_key" UNIQUE ("message_id", "display_order");



ALTER TABLE ONLY "public"."message_citations"
    ADD CONSTRAINT "message_citations_pkey" PRIMARY KEY ("message_citation_id");



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_conversation_id_message_sequence_key" UNIQUE ("conversation_id", "message_sequence");



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_pkey" PRIMARY KEY ("message_id");



ALTER TABLE ONLY "public"."permissions"
    ADD CONSTRAINT "permissions_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."permissions"
    ADD CONSTRAINT "permissions_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."permissions"
    ADD CONSTRAINT "permissions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_pkey" PRIMARY KEY ("program_course_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_program_id_course_id_key" UNIQUE ("program_id", "course_id");



ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_department_id_code_key" UNIQUE ("department_id", "code");



ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_pkey" PRIMARY KEY ("program_id");



ALTER TABLE ONLY "public"."retrieval_operations"
    ADD CONSTRAINT "retrieval_operations_pkey" PRIMARY KEY ("retrieval_operation_id");



ALTER TABLE ONLY "public"."retrieved_chunks"
    ADD CONSTRAINT "retrieved_chunks_pkey" PRIMARY KEY ("retrieval_operation_id", "chunk_id");



ALTER TABLE ONLY "public"."retrieved_chunks"
    ADD CONSTRAINT "retrieved_chunks_retrieval_rank_key" UNIQUE ("retrieval_operation_id", "retrieval_rank");



ALTER TABLE ONLY "public"."role_permissions"
    ADD CONSTRAINT "role_permissions_pkey" PRIMARY KEY ("role_id", "permission_id");



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."sections"
    ADD CONSTRAINT "sections_course_offering_id_code_key" UNIQUE ("course_offering_id", "code");



ALTER TABLE ONLY "public"."sections"
    ADD CONSTRAINT "sections_pkey" PRIMARY KEY ("section_id");



ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_academic_year_id_code_key" UNIQUE ("academic_year_id", "code");



ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_academic_year_id_number_key" UNIQUE ("academic_year_id", "semester_number");



ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_id_academic_year_id_key" UNIQUE ("semester_id", "academic_year_id");



ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_pkey" PRIMARY KEY ("semester_id");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_pkey" PRIMARY KEY ("user_id", "role_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_auth_user_id_key" UNIQUE ("auth_user_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



CREATE UNIQUE INDEX "academic_years_one_current_per_institution_idx" ON "public"."academic_years" USING "btree" ("institution_id") WHERE ("is_current" = true);



CREATE INDEX "course_offerings_program_id_idx" ON "public"."course_offerings" USING "btree" ("program_id");



CREATE INDEX "idx_conversations_user_id" ON "public"."conversations" USING "btree" ("user_id");



CREATE INDEX "idx_document_processing_runs_document_version_id" ON "public"."document_processing_runs" USING "btree" ("document_version_id");



CREATE INDEX "idx_document_versions_document_id" ON "public"."document_versions" USING "btree" ("document_id");



CREATE INDEX "idx_document_versions_supersedes_version_id" ON "public"."document_versions" USING "btree" ("supersedes_version_id");



CREATE INDEX "idx_documents_knowledge_source_id" ON "public"."documents" USING "btree" ("knowledge_source_id");



CREATE INDEX "idx_knowledge_chunks_processing_run_id" ON "public"."knowledge_chunks" USING "btree" ("processing_run_id");



CREATE INDEX "idx_knowledge_sources_created_by_user_id" ON "public"."knowledge_sources" USING "btree" ("created_by_user_id");



CREATE INDEX "idx_knowledge_sources_institution_id" ON "public"."knowledge_sources" USING "btree" ("institution_id");



CREATE INDEX "idx_knowledge_sources_owner_user_id" ON "public"."knowledge_sources" USING "btree" ("owner_user_id");



CREATE INDEX "idx_message_citations_message_id" ON "public"."message_citations" USING "btree" ("message_id");



CREATE INDEX "idx_message_citations_retrieval_operation_id" ON "public"."message_citations" USING "btree" ("retrieval_operation_id");



CREATE INDEX "idx_retrieval_operations_ai_response_id" ON "public"."retrieval_operations" USING "btree" ("ai_response_id");



CREATE INDEX "idx_retrieved_chunks_chunk_id" ON "public"."retrieved_chunks" USING "btree" ("chunk_id");



CREATE INDEX "program_courses_course_id_idx" ON "public"."program_courses" USING "btree" ("course_id");



CREATE UNIQUE INDEX "semesters_one_current_per_academic_year_idx" ON "public"."semesters" USING "btree" ("academic_year_id") WHERE ("is_current" = true);



ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."ai_responses"
    ADD CONSTRAINT "ai_responses_message_id_fkey" FOREIGN KEY ("message_id") REFERENCES "public"."messages"("message_id");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_program_course_fkey" FOREIGN KEY ("program_id", "course_id") REFERENCES "public"."program_courses"("program_id", "course_id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id");



ALTER TABLE ONLY "public"."course_offerings"
    ADD CONSTRAINT "course_offerings_semester_academic_year_fkey" FOREIGN KEY ("semester_id", "academic_year_id") REFERENCES "public"."semesters"("semester_id", "academic_year_id");



ALTER TABLE ONLY "public"."courses"
    ADD CONSTRAINT "courses_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."departments"("department_id");



ALTER TABLE ONLY "public"."departments"
    ADD CONSTRAINT "departments_campus_id_fkey" FOREIGN KEY ("campus_id") REFERENCES "public"."campuses"("campus_id");



ALTER TABLE ONLY "public"."departments"
    ADD CONSTRAINT "departments_institution_campus_fkey" FOREIGN KEY ("institution_id", "campus_id") REFERENCES "public"."campuses"("institution_id", "campus_id");



ALTER TABLE ONLY "public"."departments"
    ADD CONSTRAINT "departments_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."document_processing_runs"
    ADD CONSTRAINT "document_processing_runs_document_version_id_fkey" FOREIGN KEY ("document_version_id") REFERENCES "public"."document_versions"("document_version_id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_approved_by_user_id_fkey" FOREIGN KEY ("approved_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_created_by_user_id_fkey" FOREIGN KEY ("created_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("document_id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_reviewed_by_user_id_fkey" FOREIGN KEY ("reviewed_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_supersedes_version_id_fkey" FOREIGN KEY ("supersedes_version_id") REFERENCES "public"."document_versions"("document_version_id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_knowledge_source_id_fkey" FOREIGN KEY ("knowledge_source_id") REFERENCES "public"."knowledge_sources"("knowledge_source_id");



ALTER TABLE ONLY "public"."knowledge_chunks"
    ADD CONSTRAINT "knowledge_chunks_processing_run_id_fkey" FOREIGN KEY ("processing_run_id") REFERENCES "public"."document_processing_runs"("processing_run_id");



ALTER TABLE ONLY "public"."knowledge_sources"
    ADD CONSTRAINT "knowledge_sources_approved_by_user_id_fkey" FOREIGN KEY ("approved_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."knowledge_sources"
    ADD CONSTRAINT "knowledge_sources_created_by_user_id_fkey" FOREIGN KEY ("created_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."knowledge_sources"
    ADD CONSTRAINT "knowledge_sources_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."knowledge_sources"
    ADD CONSTRAINT "knowledge_sources_owner_user_id_fkey" FOREIGN KEY ("owner_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."knowledge_sources"
    ADD CONSTRAINT "knowledge_sources_reviewed_by_user_id_fkey" FOREIGN KEY ("reviewed_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."message_citations"
    ADD CONSTRAINT "message_citations_message_id_fkey" FOREIGN KEY ("message_id") REFERENCES "public"."messages"("message_id");



ALTER TABLE ONLY "public"."message_citations"
    ADD CONSTRAINT "message_citations_retrieved_chunk_fkey" FOREIGN KEY ("retrieval_operation_id", "chunk_id") REFERENCES "public"."retrieved_chunks"("retrieval_operation_id", "chunk_id");



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("conversation_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id");



ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."departments"("department_id");



ALTER TABLE ONLY "public"."retrieval_operations"
    ADD CONSTRAINT "retrieval_operations_ai_response_id_fkey" FOREIGN KEY ("ai_response_id") REFERENCES "public"."ai_responses"("ai_response_id");



ALTER TABLE ONLY "public"."retrieved_chunks"
    ADD CONSTRAINT "retrieved_chunks_chunk_id_fkey" FOREIGN KEY ("chunk_id") REFERENCES "public"."knowledge_chunks"("chunk_id");



ALTER TABLE ONLY "public"."retrieved_chunks"
    ADD CONSTRAINT "retrieved_chunks_retrieval_operation_id_fkey" FOREIGN KEY ("retrieval_operation_id") REFERENCES "public"."retrieval_operations"("retrieval_operation_id");



ALTER TABLE ONLY "public"."role_permissions"
    ADD CONSTRAINT "role_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "public"."permissions"("id");



ALTER TABLE ONLY "public"."role_permissions"
    ADD CONSTRAINT "role_permissions_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id");



ALTER TABLE ONLY "public"."sections"
    ADD CONSTRAINT "sections_course_offering_id_fkey" FOREIGN KEY ("course_offering_id") REFERENCES "public"."course_offerings"("course_offering_id");



ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_auth_user_id_fkey" FOREIGN KEY ("auth_user_id") REFERENCES "auth"."users"("id");



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON TABLE "public"."academic_years" TO "service_role";



GRANT ALL ON TABLE "public"."ai_responses" TO "service_role";



GRANT ALL ON TABLE "public"."campuses" TO "service_role";



GRANT ALL ON TABLE "public"."conversations" TO "service_role";



GRANT ALL ON TABLE "public"."course_offerings" TO "service_role";



GRANT ALL ON TABLE "public"."courses" TO "service_role";



GRANT ALL ON TABLE "public"."departments" TO "service_role";



GRANT ALL ON TABLE "public"."document_processing_runs" TO "service_role";



GRANT ALL ON TABLE "public"."document_versions" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."institutions" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_sources" TO "service_role";



GRANT ALL ON TABLE "public"."message_citations" TO "service_role";



GRANT ALL ON TABLE "public"."messages" TO "service_role";



GRANT ALL ON TABLE "public"."permissions" TO "service_role";



GRANT ALL ON TABLE "public"."program_courses" TO "service_role";



GRANT ALL ON TABLE "public"."programs" TO "service_role";



GRANT ALL ON TABLE "public"."retrieval_operations" TO "service_role";



GRANT ALL ON TABLE "public"."retrieved_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."role_permissions" TO "service_role";



GRANT ALL ON TABLE "public"."roles" TO "service_role";



GRANT ALL ON TABLE "public"."sections" TO "service_role";



GRANT ALL ON TABLE "public"."semesters" TO "service_role";



GRANT ALL ON TABLE "public"."user_roles" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";








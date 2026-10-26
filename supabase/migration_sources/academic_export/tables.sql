SET LOCAL search_path = public, extensions;
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;

CREATE TABLE "public"."departments" (
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

CREATE TABLE "public"."programs" (
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

CREATE TABLE "public"."academic_years" (
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
    CONSTRAINT "academic_years_current_active" CHECK (((NOT "is_current") OR "is_active")),
    CONSTRAINT "academic_years_date_check" CHECK (("end_date" > "start_date")),
    CONSTRAINT "academic_years_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0))
);

CREATE TABLE "public"."semesters" (
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
    CONSTRAINT "academic_semesters_current_active" CHECK (((NOT "is_current") OR "is_active")),
    CONSTRAINT "semesters_code_check" CHECK (("length"(TRIM(BOTH FROM "code")) > 0)),
    CONSTRAINT "semesters_date_check" CHECK (("end_date" > "start_date")),
    CONSTRAINT "semesters_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0)),
    CONSTRAINT "semesters_number_check" CHECK (("semester_number" > 0))
);

CREATE TABLE "public"."courses" (
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

CREATE TABLE "public"."program_courses" (
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

CREATE TABLE "public"."course_offerings" (
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

CREATE TABLE "public"."sections" (
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

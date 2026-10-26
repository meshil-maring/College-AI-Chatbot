ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_active_dates_exclusion" EXCLUDE USING "gist" ("institution_id" WITH =, "daterange"("start_date", "end_date", '[]'::"text") WITH &&) WHERE ("is_active");

ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_institution_id_code_key" UNIQUE ("institution_id", "code");

ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_pkey" PRIMARY KEY ("academic_year_id");

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

ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_pkey" PRIMARY KEY ("program_course_id");

ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_program_id_course_id_key" UNIQUE ("program_id", "course_id");

ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_department_id_code_key" UNIQUE ("department_id", "code");

ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_pkey" PRIMARY KEY ("program_id");

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

ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");

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

ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id");

ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id");

ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id");

ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."departments"("department_id");

ALTER TABLE ONLY "public"."sections"
    ADD CONSTRAINT "sections_course_offering_id_fkey" FOREIGN KEY ("course_offering_id") REFERENCES "public"."course_offerings"("course_offering_id");

ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id");

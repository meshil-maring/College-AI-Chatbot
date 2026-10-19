


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



CREATE OR REPLACE FUNCTION "public"."academic_master_tenant"("p_entity" "text", "p_id" "uuid") RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE result uuid;
BEGIN
    CASE p_entity
    WHEN 'departments' THEN SELECT d.institution_id INTO result FROM public.departments d WHERE d.department_id=p_id;
    WHEN 'academic_years' THEN SELECT y.institution_id INTO result FROM public.academic_years y WHERE y.academic_year_id=p_id;
    WHEN 'programs' THEN SELECT d.institution_id INTO result FROM public.programs p JOIN public.departments d USING(department_id) WHERE p.program_id=p_id;
    WHEN 'courses' THEN SELECT d.institution_id INTO result FROM public.courses c JOIN public.departments d USING(department_id) WHERE c.course_id=p_id;
    WHEN 'semesters' THEN SELECT y.institution_id INTO result FROM public.semesters s JOIN public.academic_years y USING(academic_year_id) WHERE s.semester_id=p_id;
    WHEN 'program_courses' THEN SELECT public.academic_master_tenant('programs', pc.program_id) INTO result FROM public.program_courses pc WHERE pc.program_course_id=p_id;
    WHEN 'course_offerings' THEN SELECT public.academic_master_tenant('courses', o.course_id) INTO result FROM public.course_offerings o WHERE o.course_offering_id=p_id;
    WHEN 'sections' THEN SELECT public.academic_master_tenant('course_offerings', s.course_offering_id) INTO result FROM public.sections s WHERE s.section_id=p_id;
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE='22023';
    END CASE;
    RETURN result;
END;
$$;


ALTER FUNCTION "public"."academic_master_tenant"("p_entity" "text", "p_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."assert_faculty_academic_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_permission" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE ctx jsonb;
BEGIN
    IF p_permission NOT IN ('attendance.manage','results.manage') THEN RAISE EXCEPTION 'Unsupported teaching permission' USING ERRCODE='42501'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || p_tenant::text, 0));
    SELECT jsonb_build_object('course_offering_id', co.course_offering_id,
        'semester_id', co.semester_id, 'academic_year_id', co.academic_year_id,
        'program_id', co.program_id) INTO ctx
    FROM users u JOIN user_roles ur ON ur.user_id = u.id
    JOIN roles role ON role.id = ur.role_id
    JOIN role_permissions rp ON rp.role_id = role.id
    JOIN permissions perm ON perm.permission_id = rp.permission_id
    JOIN institutions i ON i.institution_id = p_tenant
    JOIN faculty_section_assignments a ON a.faculty_user_id = u.id AND a.institution_id = p_tenant
    JOIN sections sec ON sec.section_id = a.section_id
    JOIN course_offerings co ON co.course_offering_id = sec.course_offering_id
    JOIN courses c ON c.course_id = co.course_id
    JOIN departments d ON d.department_id = c.department_id
    JOIN programs prog ON prog.program_id = co.program_id
    JOIN departments pd ON pd.department_id = prog.department_id
    JOIN semesters sem ON sem.semester_id = co.semester_id
    JOIN academic_years yr ON yr.academic_year_id = co.academic_year_id
    WHERE u.id = p_actor AND u.status = 'active' AND role.name = 'faculty' AND role.is_active
      AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
      AND perm.is_active AND perm.code IN (p_permission, split_part(p_permission,'.',1)||'.*', '*')
      AND i.status = 'active' AND i.is_active AND sec.section_id = p_section
      AND sec.is_active AND co.is_active AND c.is_active AND d.is_active
      AND prog.is_active AND pd.is_active AND sem.is_active AND yr.is_active
      AND d.institution_id = p_tenant AND pd.institution_id = p_tenant AND yr.institution_id = p_tenant
      AND sem.academic_year_id = co.academic_year_id
      AND a.is_active AND a.revoked_at IS NULL AND a.start_at <= clock_timestamp()
      AND (a.end_at IS NULL OR clock_timestamp() < a.end_at)
    LIMIT 1 FOR SHARE OF u, ur, role, rp, perm, i, a, sec, co, c, d, prog, pd, sem, yr;
    IF ctx IS NULL THEN RAISE EXCEPTION 'Teaching mutation denied' USING ERRCODE = '42501'; END IF;
    RETURN ctx;
END; $$;


ALTER FUNCTION "public"."assert_faculty_academic_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_permission" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."assert_faculty_attendance_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid") RETURNS "jsonb"
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
 SELECT public.assert_faculty_academic_mutation(p_actor,p_tenant,p_section,'attendance.manage');
$$;


ALTER FUNCTION "public"."assert_faculty_attendance_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid") OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."faculty_tests" (
    "test_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "section_id" "uuid" NOT NULL,
    "title" "text" NOT NULL,
    "test_type" "text" NOT NULL,
    "description" "text",
    "max_marks" numeric(8,2) NOT NULL,
    "passing_marks" numeric(8,2),
    "scheduled_date" "date",
    "start_time" time without time zone,
    "end_time" time without time zone,
    "duration_minutes" integer,
    "status" "text" DEFAULT 'DRAFT'::"text" NOT NULL,
    "marks_state" "text" DEFAULT 'DRAFT'::"text" NOT NULL,
    "version" bigint DEFAULT 1 NOT NULL,
    "created_by" "uuid" NOT NULL,
    "updated_by" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "faculty_tests_check" CHECK ((("passing_marks" >= (0)::numeric) AND ("passing_marks" <= "max_marks"))),
    CONSTRAINT "faculty_tests_check1" CHECK (((("start_time" IS NULL) AND ("end_time" IS NULL)) OR (("scheduled_date" IS NOT NULL) AND ("start_time" IS NOT NULL) AND ("end_time" IS NOT NULL) AND ("end_time" > "start_time")))),
    CONSTRAINT "faculty_tests_check2" CHECK ((("status" = ANY (ARRAY['DRAFT'::"text", 'CANCELLED'::"text"])) OR ("scheduled_date" IS NOT NULL))),
    CONSTRAINT "faculty_tests_description_check" CHECK (("length"("description") <= 4000)),
    CONSTRAINT "faculty_tests_duration_minutes_check" CHECK ((("duration_minutes" >= 1) AND ("duration_minutes" <= 1440))),
    CONSTRAINT "faculty_tests_marks_state_check" CHECK (("marks_state" = ANY (ARRAY['DRAFT'::"text", 'SUBMITTED'::"text"]))),
    CONSTRAINT "faculty_tests_max_marks_check" CHECK (("max_marks" > (0)::numeric)),
    CONSTRAINT "faculty_tests_status_check" CHECK (("status" = ANY (ARRAY['DRAFT'::"text", 'SCHEDULED'::"text", 'ONGOING'::"text", 'COMPLETED'::"text", 'PUBLISHED'::"text", 'LOCKED'::"text", 'CANCELLED'::"text"]))),
    CONSTRAINT "faculty_tests_title_check" CHECK ((("length"("btrim"("title")) >= 1) AND ("length"("btrim"("title")) <= 160)))
);


ALTER TABLE "public"."faculty_tests" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."assert_test_version"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint) RETURNS "public"."faculty_tests"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE t public.faculty_tests;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||p_tenant::text,0));
 SELECT * INTO t FROM faculty_tests WHERE test_id=p_test AND institution_id=p_tenant FOR UPDATE;
 IF t.test_id IS NULL THEN RAISE EXCEPTION 'Assessment not found' USING ERRCODE='P0002'; END IF;
 PERFORM assert_faculty_academic_mutation(p_actor,p_tenant,t.section_id,'results.manage');
 IF t.created_by<>p_actor THEN RAISE EXCEPTION 'Assessment belongs to another teacher' USING ERRCODE='42501'; END IF;
 IF t.version IS DISTINCT FROM p_version THEN RAISE EXCEPTION 'Assessment changed; reload before saving' USING ERRCODE='40001'; END IF;
 PERFORM set_config('collegeai.test_write','rpc',true);
 RETURN t;
END; $$;


ALTER FUNCTION "public"."assert_test_version"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."commit_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_expected_updated_at" timestamp with time zone, "p_rows" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE item public.faculty_attendance_imports; ctx jsonb; row jsonb; data jsonb; identity jsonb;
    roster public.faculty_attendance_rosters; old public.faculty_attendance_rosters;
    count_rows integer := 0; attendance_date date; student uuid;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || p_tenant::text, 0));
    SELECT * INTO item FROM faculty_attendance_imports WHERE import_id = p_import_id AND institution_id = p_tenant FOR UPDATE;
    IF item.import_id IS NULL OR item.uploaded_by <> p_actor THEN RAISE EXCEPTION 'Import scope denied' USING ERRCODE = '42501'; END IF;
    ctx := assert_faculty_attendance_mutation(p_actor, p_tenant, item.section_id);
    IF item.status NOT IN ('VALIDATED','REVIEWED') OR item.updated_at IS DISTINCT FROM p_expected_updated_at THEN
        RAISE EXCEPTION 'Import changed or already committed' USING ERRCODE = '40001';
    END IF;
    IF jsonb_array_length(p_rows) NOT BETWEEN 1 AND 500 OR jsonb_array_length(p_rows) <>
        (SELECT count(*) FROM faculty_attendance_import_rows WHERE import_id = p_import_id AND row_number >= 2)
        OR EXISTS(SELECT 1 FROM faculty_attendance_import_rows WHERE import_id = p_import_id AND validation_status IN ('ERROR','DUPLICATE','CONFLICT')) THEN
        RAISE EXCEPTION 'Review errors remain' USING ERRCODE = '23514';
    END IF;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.review', 'faculty_attendance_imports', p_import_id::text,
        jsonb_build_object('validated_rows', jsonb_array_length(p_rows)), 'success');
    FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        IF row->'errors' <> '[]'::jsonb OR NOT EXISTS(SELECT 1 FROM faculty_attendance_import_rows
            WHERE import_id = p_import_id AND row_number = (row->>'row_number')::integer AND raw_data = row->'raw_data') THEN
            RAISE EXCEPTION 'Review changed' USING ERRCODE = '40001';
        END IF;
        data := row->'normalized_data';
        IF nullif(btrim(data->>'register_number'),'') IS NULL OR nullif(btrim(data->>'student_name'),'') IS NULL THEN
            RAISE EXCEPTION 'Missing identity' USING ERRCODE = '23514';
        END IF;
        identity := faculty_attendance_identity(p_tenant, data->>'register_number', data->>'university_roll_number');
        IF (identity->>'conflict')::boolean OR
            (identity->>'program_id' IS NOT NULL AND identity->>'program_id' <> ctx->>'program_id') OR
            (identity->>'academic_year_id' IS NOT NULL AND identity->>'academic_year_id' <> ctx->>'academic_year_id') THEN
            RAISE EXCEPTION 'Identity conflict' USING ERRCODE = '23514';
        END IF;
        student := CASE WHEN identity->>'approval_status' = 'approved' THEN (identity->>'student_id')::uuid ELSE NULL END;
        SELECT * INTO old FROM faculty_attendance_rosters WHERE institution_id = p_tenant AND section_id = item.section_id
            AND register_number = data->>'register_number' FOR UPDATE;
        IF old.roster_id IS NOT NULL AND ((old.linked_student_id IS NOT NULL AND old.linked_student_id IS DISTINCT FROM student)
            OR (nullif(old.university_roll_number,'') IS NOT NULL AND nullif(data->>'university_roll_number','') IS NOT NULL
                AND old.university_roll_number <> data->>'university_roll_number')) THEN
            RAISE EXCEPTION 'Existing roster identity conflict' USING ERRCODE = '23514';
        END IF;
        INSERT INTO faculty_attendance_rosters(institution_id, section_id, course_offering_id, semester_id,
            register_number, university_roll_number, student_name, email, created_by, linked_student_id,
            roster_status, imported_summary, source_metadata, reconciliation_state)
        VALUES(p_tenant, item.section_id, item.course_offering_id, item.semester_id, data->>'register_number',
            nullif(data->>'university_roll_number',''), data->>'student_name', nullif(data->>'email',''), p_actor, student,
            CASE WHEN identity->>'student_id' IS NULL THEN 'UNREGISTERED' WHEN student IS NULL THEN 'PENDING_APPROVAL'
                 WHEN identity->>'is_active' = 'true' AND identity->>'status' = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END,
            row->'imported_summary', jsonb_build_object('import_id', p_import_id),
            CASE WHEN student IS NOT NULL THEN 'LINKED' WHEN identity->>'student_id' IS NOT NULL THEN 'PENDING' ELSE 'NONE' END)
        ON CONFLICT(institution_id, section_id, register_number) DO UPDATE SET
            university_roll_number = coalesce(EXCLUDED.university_roll_number, faculty_attendance_rosters.university_roll_number),
            student_name = EXCLUDED.student_name, email = coalesce(EXCLUDED.email, faculty_attendance_rosters.email),
            linked_student_id = coalesce(faculty_attendance_rosters.linked_student_id, EXCLUDED.linked_student_id),
            roster_status = EXCLUDED.roster_status, reconciliation_state = EXCLUDED.reconciliation_state,
            imported_summary = EXCLUDED.imported_summary, source_metadata = EXCLUDED.source_metadata
        RETURNING * INTO roster;
        IF nullif(data->>'status','') IS NOT NULL THEN
            attendance_date := (data->>'session_date')::date;
            PERFORM mark_faculty_attendance(p_actor, p_tenant, item.section_id, attendance_date,
                jsonb_build_object(roster.roster_id::text, data->>'status'), NULL);
        END IF;
        count_rows := count_rows + 1;
    END LOOP;
    UPDATE faculty_attendance_imports SET status = 'IMPORTED', summary = summary || jsonb_build_object('imported', count_rows, 'rejected', 0)
      WHERE import_id = p_import_id;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.commit', 'faculty_attendance_imports', p_import_id::text,
        jsonb_build_object('imported_rows', count_rows), 'success');
    RETURN jsonb_build_object('import_id', p_import_id, 'imported_rows', count_rows, 'status', 'IMPORTED');
END; $$;


ALTER FUNCTION "public"."commit_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_expected_updated_at" timestamp with time zone, "p_rows" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."commit_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_version" bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE i public.faculty_attendance_imports; t public.faculty_tests; row public.faculty_attendance_import_rows;
 r public.faculty_attendance_rosters; marks jsonb:='[]'; seen uuid[]:='{}'; result jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||p_tenant::text,0));
 SELECT * INTO i FROM faculty_attendance_imports WHERE import_id=p_import AND institution_id=p_tenant AND test_id IS NOT NULL FOR UPDATE;
 IF i.import_id IS NULL THEN RAISE EXCEPTION 'Import not found' USING ERRCODE='P0002'; END IF;
 t:=assert_test_version(p_actor,p_tenant,i.test_id,p_version);
 IF i.uploaded_by<>p_actor THEN RAISE EXCEPTION 'Import owner denied' USING ERRCODE='42501'; END IF;
 IF i.status='IMPORTED' OR i.updated_at IS DISTINCT FROM p_updated_at THEN RAISE EXCEPTION 'Import changed or already committed' USING ERRCODE='40001'; END IF;
 FOR row IN SELECT * FROM faculty_attendance_import_rows WHERE import_id=p_import ORDER BY row_number LOOP
   IF row.validation_status NOT IN ('VALID','UPDATE') OR row.errors<>'[]'::jsonb THEN
     RAISE EXCEPTION 'Review errors remain' USING ERRCODE='23514'; END IF;
   SELECT * INTO r FROM faculty_attendance_rosters WHERE institution_id=p_tenant AND section_id=t.section_id
     AND register_number=row.normalized_data->>'register_number' FOR SHARE;
   IF r.roster_id IS NULL OR r.roster_id=ANY(seen) OR r.reconciliation_state='CONFLICT' OR
     (nullif(row.normalized_data->>'university_roll_number','') IS NOT NULL AND
       r.university_roll_number IS DISTINCT FROM row.normalized_data->>'university_roll_number') THEN
     RAISE EXCEPTION 'Import identity changed or conflicts' USING ERRCODE='23514'; END IF;
   seen:=array_append(seen,r.roster_id);
   marks:=marks||jsonb_build_array(jsonb_build_object('roster_id',r.roster_id,'scored_marks',nullif(row.normalized_data->>'scored_marks',''),
     'mark_status',row.normalized_data->>'mark_status','remarks',row.normalized_data->>'remarks'));
 END LOOP;
 result:=save_faculty_test_marks(p_actor,p_tenant,i.test_id,p_version,marks);
 UPDATE faculty_attendance_imports SET status='IMPORTED',summary=summary||jsonb_build_object('imported',jsonb_array_length(marks)) WHERE import_id=p_import;
 INSERT INTO admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
 VALUES(p_actor,p_tenant,'test.import.commit','faculty_tests',i.test_id::text,jsonb_build_object('import_id',p_import,'count',jsonb_array_length(marks)),'success');
 RETURN result||jsonb_build_object('import_id',p_import,'status','IMPORTED');
END; $$;


ALTER FUNCTION "public"."commit_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_version" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."consume_auth_password_recovery_session"("p_session_fingerprint" "text", "p_auth_user_id" "uuid", "p_expires_at" timestamp with time zone) RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    inserted_rows integer;
BEGIN
    DELETE FROM "public"."auth_consumed_password_recovery_sessions"
    WHERE "expires_at" <= pg_catalog.now();

    INSERT INTO "public"."auth_consumed_password_recovery_sessions" (
        "session_fingerprint",
        "auth_user_id",
        "expires_at"
    )
    VALUES (
        "p_session_fingerprint",
        "p_auth_user_id",
        "p_expires_at"
    )
    ON CONFLICT ("session_fingerprint") DO NOTHING;

    GET DIAGNOSTICS inserted_rows = ROW_COUNT;
    RETURN inserted_rows = 1;
END;
$$;


ALTER FUNCTION "public"."consume_auth_password_recovery_session"("p_session_fingerprint" "text", "p_auth_user_id" "uuid", "p_expires_at" timestamp with time zone) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE result_id uuid;
BEGIN
    result_id := public.phase81_manage_faculty_section_assignment(p_actor_user_id, p_institution_id,
        p_faculty_user_id, p_section_id, false);
    PERFORM public.update_faculty_teaching_validity(p_actor_user_id, p_institution_id,
        result_id, p_start_at, p_end_at, p_is_active);
    RETURN result_id;
END; $$;


ALTER FUNCTION "public"."create_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_assignment_touch"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END; $$;


ALTER FUNCTION "public"."faculty_assignment_touch"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_attendance_context_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE tenant uuid; offering uuid; semester uuid; year_id uuid;
BEGIN
    SELECT d.institution_id, sec.course_offering_id, co.semester_id, co.academic_year_id
    INTO tenant, offering, semester, year_id FROM sections sec
    JOIN course_offerings co ON co.course_offering_id=sec.course_offering_id
    JOIN courses c ON c.course_id=co.course_id JOIN departments d ON d.department_id=c.department_id
    WHERE sec.section_id=NEW.section_id;
    IF tenant IS NULL OR NEW.institution_id IS DISTINCT FROM tenant OR NEW.course_offering_id IS DISTINCT FROM offering THEN
        RAISE EXCEPTION 'Attendance academic scope mismatch' USING ERRCODE='23514';
    END IF;
    IF TG_TABLE_NAME='faculty_attendance_rosters' THEN
        IF NEW.semester_id IS DISTINCT FROM semester THEN RAISE EXCEPTION 'Roster semester mismatch' USING ERRCODE='23514'; END IF;
        IF NEW.linked_student_id IS NOT NULL THEN
            IF NOT EXISTS(SELECT 1 FROM students WHERE student_id=NEW.linked_student_id AND institution_id=tenant) THEN
                RAISE EXCEPTION 'Linked student tenant mismatch' USING ERRCODE='23514';
            END IF;
        END IF;
    ELSIF TG_TABLE_NAME='faculty_attendance_imports' THEN
        IF NEW.semester_id IS DISTINCT FROM semester OR NEW.academic_year_id IS DISTINCT FROM year_id THEN
            RAISE EXCEPTION 'Import academic scope mismatch' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END; $$;


ALTER FUNCTION "public"."faculty_attendance_context_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_attendance_identity"("p_tenant" "uuid", "p_register" "text", "p_roll" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE ids uuid[]; s public.students;
BEGIN
    SELECT array_agg(student_id) INTO ids FROM students
    WHERE institution_id = p_tenant AND
      ((nullif(btrim(p_register), '') IS NOT NULL AND register_number = btrim(p_register)) OR
       (nullif(btrim(p_roll), '') IS NOT NULL AND university_roll_number = btrim(p_roll)));
    IF cardinality(ids) > 1 THEN RETURN '{"conflict":true}'::jsonb; END IF;
    IF ids IS NULL THEN RETURN '{"conflict":false}'::jsonb; END IF;
    SELECT * INTO s FROM students WHERE student_id = ids[1] FOR SHARE;
    IF (nullif(btrim(p_register),'') IS NOT NULL AND nullif(s.register_number,'') IS NOT NULL AND s.register_number <> btrim(p_register))
       OR (nullif(btrim(p_roll),'') IS NOT NULL AND nullif(s.university_roll_number,'') IS NOT NULL AND s.university_roll_number <> btrim(p_roll)) THEN
        RETURN '{"conflict":true}'::jsonb;
    END IF;
    RETURN jsonb_build_object('conflict', false, 'student_id', s.student_id,
        'approval_status', s.approval_status, 'is_active', s.is_active, 'status', s.status,
        'program_id', s.program_id, 'academic_year_id', s.academic_year_id);
END; $$;


ALTER FUNCTION "public"."faculty_attendance_identity"("p_tenant" "uuid", "p_register" "text", "p_roll" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_attendance_record_scope_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
    session_section uuid;
    roster_section uuid;
BEGIN
    SELECT section_id INTO session_section FROM faculty_attendance_sessions WHERE session_id = NEW.session_id;
    SELECT section_id INTO roster_section FROM faculty_attendance_rosters WHERE roster_id = NEW.roster_id;
    IF session_section IS NULL OR roster_section IS NULL OR session_section IS DISTINCT FROM roster_section THEN
        RAISE EXCEPTION 'attendance record session and roster must belong to the same section';
    END IF;
    RETURN NEW;
END; $$;


ALTER FUNCTION "public"."faculty_attendance_record_scope_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_attendance_set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END; $$;


ALTER FUNCTION "public"."faculty_attendance_set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_responsibility_scope_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
DECLARE
    scope_department uuid;
    scope_institution uuid;
    scope_program uuid;
    scope_semester uuid;
    scope_year uuid;
    scope_section_code text;
    scope_course uuid;
    exclusive boolean;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.revoked_at IS NOT NULL
       AND NEW.institution_id = OLD.institution_id AND NEW.faculty_user_id = OLD.faculty_user_id
       AND NEW.responsibility_code = OLD.responsibility_code AND NEW.scope_type = OLD.scope_type
       AND NEW.scope_id = OLD.scope_id THEN
        NEW.updated_at := now();
        RETURN NEW;
    END IF;
    SELECT exclusive_scope INTO exclusive FROM public.responsibility_definitions
    WHERE code = NEW.responsibility_code AND is_active AND NEW.scope_type = ANY(allowed_scope_types);
    IF NOT FOUND THEN RAISE EXCEPTION 'Invalid responsibility definition or scope' USING ERRCODE = '23514'; END IF;
    IF NEW.scope_type = 'institution' THEN
        scope_institution := NEW.scope_id;
    ELSIF NEW.scope_type = 'department' THEN
        SELECT department_id, institution_id INTO scope_department, scope_institution
        FROM public.departments WHERE department_id = NEW.scope_id AND is_active;
    ELSIF NEW.scope_type = 'program' THEN
        SELECT p.program_id, p.department_id, d.institution_id INTO scope_program, scope_department, scope_institution
        FROM public.programs p JOIN public.departments d USING(department_id)
        WHERE p.program_id = NEW.scope_id AND p.is_active AND d.is_active;
    ELSIF NEW.scope_type = 'semester' THEN
        SELECT p.program_id, p.department_id, d.institution_id, s.semester_id, s.academic_year_id
        INTO scope_program, scope_department, scope_institution, scope_semester, scope_year
        FROM public.programs p JOIN public.departments d USING(department_id) CROSS JOIN public.semesters s
        JOIN public.academic_years ay ON ay.academic_year_id = s.academic_year_id
        WHERE p.program_id = NEW.program_id AND s.semester_id = NEW.scope_id AND p.is_active AND d.is_active AND s.is_active
          AND ay.is_active AND ay.institution_id = d.institution_id;
    ELSIF NEW.scope_type = 'course' THEN
        SELECT c.course_id, c.department_id, d.institution_id INTO scope_course, scope_department, scope_institution
        FROM public.courses c JOIN public.departments d USING(department_id)
        WHERE c.course_id = NEW.scope_id AND c.is_active AND d.is_active;
    ELSIF NEW.scope_type = 'section' THEN
        SELECT c.department_id, d.institution_id, co.program_id, co.semester_id, co.academic_year_id, s.code
        INTO scope_department, scope_institution, scope_program, scope_semester, scope_year, scope_section_code
        FROM public.sections s JOIN public.course_offerings co USING(course_offering_id)
        JOIN public.courses c USING(course_id) JOIN public.departments d ON d.department_id = c.department_id
        JOIN public.programs p ON p.program_id = co.program_id
        JOIN public.departments pd ON pd.department_id = p.department_id
        JOIN public.semesters sem ON sem.semester_id = co.semester_id
        JOIN public.academic_years ay ON ay.academic_year_id = co.academic_year_id
        WHERE s.section_id = NEW.scope_id AND s.is_active AND co.is_active AND c.is_active
          AND d.is_active AND p.is_active AND sem.is_active AND ay.is_active
          AND pd.is_active AND pd.institution_id = d.institution_id
          AND sem.academic_year_id = co.academic_year_id
          AND ay.institution_id = d.institution_id;
    END IF;
    IF scope_institution IS NULL OR scope_institution <> NEW.institution_id OR NOT EXISTS (
        SELECT 1 FROM public.institutions WHERE institution_id = scope_institution AND status = 'active' AND is_active
    ) THEN RAISE EXCEPTION 'Responsibility scope is outside the active institution' USING ERRCODE = '23514'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id WHERE u.id = NEW.faculty_user_id AND u.status = 'active'
        AND r.name = 'faculty' AND r.is_active AND ur.scope_type = 'institution' AND ur.scope_id = NEW.institution_id
    ) THEN RAISE EXCEPTION 'Active Faculty in the institution required' USING ERRCODE = '23514'; END IF;
    NEW.department_id := scope_department;
    NEW.program_id := scope_program;
    NEW.semester_id := scope_semester;
    NEW.academic_year_id := scope_year;
    NEW.section_id := CASE WHEN NEW.scope_type = 'section' THEN NEW.scope_id ELSE NULL END;
    NEW.section_code := scope_section_code;
    NEW.course_id := scope_course;
    NEW.exclusive_scope := exclusive;
    NEW.scope_key := CASE WHEN NEW.scope_type = 'section' THEN
        concat(scope_program, ':', scope_year, ':', scope_semester, ':', scope_section_code)
        WHEN NEW.scope_type = 'semester' THEN concat(scope_program, ':', scope_semester)
        ELSE NEW.scope_id::text END;
    NEW.updated_at := now();
    -- RPCs and table writes serialize appointments for each tenant. The
    -- exclusion constraint below also covers concurrent transaction snapshots.
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(NEW.institution_id::text, 110));
    IF NEW.is_active AND NEW.revoked_at IS NULL AND EXISTS (
        SELECT 1 FROM public.faculty_responsibilities f
        WHERE f.institution_id = NEW.institution_id AND f.responsibility_code = NEW.responsibility_code
        AND f.scope_type = NEW.scope_type AND f.scope_key = NEW.scope_key
        AND f.responsibility_id <> NEW.responsibility_id AND f.is_active AND f.revoked_at IS NULL
        AND (exclusive OR f.faculty_user_id = NEW.faculty_user_id)
        AND tstzrange(f.start_at, f.end_at, '[)') && tstzrange(NEW.start_at, NEW.end_at, '[)')
    ) THEN RAISE EXCEPTION 'Overlapping responsibility appointment' USING ERRCODE = '23P01'; END IF;
    RETURN NEW;
END; $$;


ALTER FUNCTION "public"."faculty_responsibility_scope_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."faculty_test_context_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
DECLARE tenant uuid;
BEGIN
 SELECT d.institution_id INTO tenant FROM sections s JOIN course_offerings co USING(course_offering_id)
 JOIN courses c USING(course_id) JOIN departments d USING(department_id) WHERE s.section_id=NEW.section_id;
 IF tenant IS NULL OR tenant<>NEW.institution_id OR current_setting('collegeai.test_write',true) IS DISTINCT FROM 'rpc' THEN
   RAISE EXCEPTION 'Assessment writes require the authorized transaction' USING ERRCODE='42501';
 END IF;
 IF TG_OP='UPDATE' AND (NEW.section_id<>OLD.section_id OR NEW.institution_id<>OLD.institution_id OR NEW.created_by<>OLD.created_by) THEN
   RAISE EXCEPTION 'Assessment ownership is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;


ALTER FUNCTION "public"."faculty_test_context_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."guard_test_import_workflow"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE parent_test uuid;
BEGIN
 IF TG_TABLE_NAME='faculty_attendance_imports' THEN
   parent_test:=CASE WHEN TG_OP='DELETE' THEN OLD.test_id ELSE NEW.test_id END;
   IF TG_OP='UPDATE' AND OLD.test_id IS DISTINCT FROM NEW.test_id THEN
     RAISE EXCEPTION 'Import workflow is immutable' USING ERRCODE='23514'; END IF;
 ELSE
   SELECT test_id INTO parent_test FROM faculty_attendance_imports WHERE import_id=CASE WHEN TG_OP='DELETE' THEN OLD.import_id ELSE NEW.import_id END;
 END IF;
 IF parent_test IS NOT NULL AND current_setting('collegeai.test_write',true) IS DISTINCT FROM 'rpc' THEN
   RAISE EXCEPTION 'Assessment staging requires its authorized transaction' USING ERRCODE='42501'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END; $$;


ALTER FUNCTION "public"."guard_test_import_workflow"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."guard_workflow_result_delete"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
 IF OLD.test_id IS NOT NULL THEN RAISE EXCEPTION 'Assessment history cannot be deleted' USING ERRCODE='42501'; END IF;
 RETURN OLD;
END; $$;


ALTER FUNCTION "public"."guard_workflow_result_delete"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."manage_academic_master_record"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_entity" "text", "p_record_id" "uuid", "p_payload" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $_$
DECLARE
    id_column text;
    resource text;
    allowed text[];
    immutable text[];
    key text;
    before_row jsonb;
    after_row jsonb;
    item_id uuid := COALESCE(p_record_id, gen_random_uuid());
    fields text;
    expressions text;
    effective jsonb;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    CASE p_entity
    WHEN 'departments' THEN id_column:='department_id'; resource:='departments'; allowed:=ARRAY['name','code','description','is_active']; immutable:=ARRAY['institution_id','campus_id'];
    WHEN 'programs' THEN id_column:='program_id'; resource:='departments'; allowed:=ARRAY['department_id','name','code','description','degree_type','duration_years','total_credits','is_active']; immutable:=ARRAY['department_id'];
    WHEN 'academic_years' THEN id_column:='academic_year_id'; resource:='academic_years'; allowed:=ARRAY['name','code','start_date','end_date','is_current','is_active']; immutable:=ARRAY['institution_id'];
    WHEN 'semesters' THEN id_column:='semester_id'; resource:='semesters'; allowed:=ARRAY['academic_year_id','name','code','semester_number','start_date','end_date','is_current','is_active']; immutable:=ARRAY['academic_year_id'];
    WHEN 'courses' THEN id_column:='course_id'; resource:='courses'; allowed:=ARRAY['department_id','name','code','description','credits','lecture_hours','tutorial_hours','practical_hours','is_active']; immutable:=ARRAY['department_id'];
    WHEN 'program_courses' THEN id_column:='program_course_id'; resource:='courses'; allowed:=ARRAY['program_id','course_id','semester_id','course_type','is_required','is_active']; immutable:=ARRAY['program_id','course_id','semester_id'];
    WHEN 'course_offerings' THEN id_column:='course_offering_id'; resource:='courses'; allowed:=ARRAY['course_id','program_id','academic_year_id','semester_id','capacity','is_active']; immutable:=ARRAY['course_id','program_id','academic_year_id','semester_id'];
    WHEN 'sections' THEN id_column:='section_id'; resource:='courses'; allowed:=ARRAY['course_offering_id','name','code','capacity','is_active']; immutable:=ARRAY['course_offering_id','code'];
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE='22023';
    END CASE;
    IF NOT EXISTS(
        SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id
        JOIN public.role_permissions rp ON rp.role_id=r.id JOIN public.permissions permission ON permission.permission_id=rp.permission_id
        WHERE ur.user_id=p_actor_user_id AND ur.scope_type='institution' AND ur.scope_id=p_institution_id
          AND r.name='admin' AND r.is_active AND permission.is_active
          AND permission.code IN (resource||'.manage', resource||'.*', '*')
    ) AND NOT EXISTS(
        SELECT 1 FROM public.user_permission_grants g JOIN public.permissions permission USING(permission_id)
        WHERE g.user_id=p_actor_user_id AND g.institution_id=p_institution_id AND g.revoked_at IS NULL
          AND permission.is_active AND permission.code IN(resource||'.manage',resource||'.*','*')
    ) THEN RAISE EXCEPTION 'Academic permission required' USING ERRCODE='42501'; END IF;
    IF p_payload IS NULL OR jsonb_typeof(p_payload)<>'object' OR p_payload='{}'::jsonb THEN
        RAISE EXCEPTION 'Academic fields required' USING ERRCODE='22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT key=ANY(allowed) OR (p_record_id IS NOT NULL AND key=ANY(immutable)) THEN
            RAISE EXCEPTION 'Unsupported or immutable academic field' USING ERRCODE='22023';
        END IF;
    END LOOP;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:' || p_institution_id::text, 0));
    IF p_record_id IS NOT NULL THEN
        IF public.academic_master_tenant(p_entity, p_record_id) IS DISTINCT FROM p_institution_id THEN
            RAISE EXCEPTION 'Academic record not found' USING ERRCODE='P0002';
        END IF;
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I=$1 FOR UPDATE',p_entity,id_column) INTO before_row USING p_record_id;
    END IF;
    effective := COALESCE(before_row,'{}'::jsonb) || p_payload || jsonb_build_object(id_column,item_id);
    IF p_entity IN ('departments','academic_years') THEN
        effective := effective || jsonb_build_object('institution_id',p_institution_id);
    ELSE
        CASE p_entity
        WHEN 'programs','courses' THEN resource:=public.academic_master_tenant('departments',(effective->>'department_id')::uuid)::text;
        WHEN 'semesters' THEN resource:=public.academic_master_tenant('academic_years',(effective->>'academic_year_id')::uuid)::text;
        WHEN 'program_courses','course_offerings' THEN resource:=public.academic_master_tenant('programs',(effective->>'program_id')::uuid)::text;
        WHEN 'sections' THEN resource:=public.academic_master_tenant('course_offerings',(effective->>'course_offering_id')::uuid)::text;
        END CASE;
        IF resource IS DISTINCT FROM p_institution_id::text THEN
            RAISE EXCEPTION 'Academic parent not found' USING ERRCODE='P0002';
        END IF;
    END IF;
    -- Populate only validated keys so SQL defaults remain authoritative.
    SELECT string_agg(format('%I',k),','),string_agg(format('r.%I',k),',') INTO fields,expressions
      FROM jsonb_object_keys(CASE WHEN p_record_id IS NULL THEN effective ELSE p_payload END) AS k;
    IF p_record_id IS NULL THEN
        EXECUTE format('INSERT INTO public.%I AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::public.%I,$1) r RETURNING to_jsonb(t)',p_entity,fields,expressions,p_entity)
          INTO after_row USING effective;
    ELSE
        EXECUTE format('UPDATE public.%I AS t SET (%s)=(SELECT %s FROM jsonb_populate_record(NULL::public.%I,$1) r) WHERE %I=$2 RETURNING to_jsonb(t)',p_entity,fields,expressions,p_entity,id_column)
          INTO after_row USING effective,p_record_id;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data)
    VALUES(p_actor_user_id,p_institution_id,
        'academic.'||p_entity||CASE WHEN p_record_id IS NULL THEN '.create' WHEN p_payload->>'is_active'='false' THEN '.deactivate' WHEN p_payload->>'is_active'='true' THEN '.activate' ELSE '.update' END,
        p_entity,item_id,jsonb_build_object('before',before_row,'after',after_row));
    RETURN after_row;
END;
$_$;


ALTER FUNCTION "public"."manage_academic_master_record"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_entity" "text", "p_record_id" "uuid", "p_payload" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."manage_faculty_responsibility"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_responsibility_code" "text", "p_scope_type" "text", "p_scope_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_responsibility_id" "uuid" DEFAULT NULL::"uuid", "p_revoke" boolean DEFAULT false, "p_program_id" "uuid" DEFAULT NULL::"uuid") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE result_id uuid; before_row jsonb; after_row jsonb;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id
        JOIN public.permissions p ON p.permission_id = rp.permission_id
        JOIN public.institutions i ON i.institution_id = p_institution_id
        WHERE u.id = p_actor_user_id AND u.status = 'active' AND r.is_active
        AND p.code = 'faculty.assignments.manage' AND p.is_active AND i.is_active AND i.status = 'active'
        AND ((r.name = 'admin' AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id)
          OR (r.name = 'super_admin' AND ur.scope_type = 'platform' AND ur.scope_id IS NULL))
    ) THEN RAISE EXCEPTION 'Assignment management authority required' USING ERRCODE = '42501'; END IF;
    IF p_actor_user_id = p_faculty_user_id THEN RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501'; END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_institution_id::text, 110));
    IF p_responsibility_id IS NULL THEN
        IF p_revoke THEN RAISE EXCEPTION 'Appointment required' USING ERRCODE = '23514'; END IF;
        INSERT INTO public.faculty_responsibilities(institution_id, faculty_user_id, responsibility_code,
            scope_type, scope_id, program_id, start_at, end_at, is_active, created_by, scope_key)
        VALUES(p_institution_id, p_faculty_user_id, p_responsibility_code, p_scope_type, p_scope_id,
            p_program_id, p_start_at, p_end_at, p_is_active, p_actor_user_id, '')
        RETURNING responsibility_id, to_jsonb(faculty_responsibilities.*) INTO result_id, after_row;
    ELSE
        SELECT to_jsonb(f.*) INTO before_row FROM public.faculty_responsibilities f
        WHERE f.responsibility_id = p_responsibility_id AND f.institution_id = p_institution_id
        AND f.faculty_user_id = p_faculty_user_id AND f.revoked_at IS NULL FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Appointment not found' USING ERRCODE = 'P0002'; END IF;
        IF p_revoke THEN
            -- Revocation must work even if the faculty account or scope has
            -- since been deactivated. The guard skips immutable scope checks.
            UPDATE public.faculty_responsibilities SET revoked_at = now(), revoked_by = p_actor_user_id, is_active = false
            WHERE responsibility_id = p_responsibility_id
            RETURNING responsibility_id, to_jsonb(faculty_responsibilities.*) INTO result_id, after_row;
        ELSE
            UPDATE public.faculty_responsibilities SET scope_type = p_scope_type, scope_id = p_scope_id,
                program_id = p_program_id, start_at = p_start_at, end_at = p_end_at, is_active = p_is_active
            WHERE responsibility_id = p_responsibility_id
            RETURNING responsibility_id, to_jsonb(faculty_responsibilities.*) INTO result_id, after_row;
        END IF;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor_user_id, p_institution_id, CASE WHEN p_revoke THEN 'faculty.responsibility.revoke'
        WHEN before_row IS NULL THEN 'faculty.responsibility.create' ELSE 'faculty.responsibility.update' END,
        'faculty_responsibilities', result_id::text, jsonb_build_object('before',before_row,'after',after_row), 'success');
    RETURN result_id;
END; $$;


ALTER FUNCTION "public"."manage_faculty_responsibility"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_responsibility_code" "text", "p_scope_type" "text", "p_scope_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_responsibility_id" "uuid", "p_revoke" boolean, "p_program_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."manage_scoped_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_revoke" boolean DEFAULT false) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    target_faculty uuid;
    target_section uuid;
    target_department uuid;
    target_program uuid;
    target_year uuid;
    target_semester uuid;
    target_section_code text;
    target_course uuid;
    before_row jsonb;
    after_row jsonb;
    result_id uuid;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;

    IF p_actor_user_id = p_faculty_user_id AND p_assignment_id IS NULL THEN
        RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501';
    END IF;

    IF p_assignment_id IS NOT NULL THEN
        SELECT to_jsonb(a.*), a.faculty_user_id, a.section_id
        INTO before_row, target_faculty, target_section
        FROM public.faculty_section_assignments AS a
        WHERE a.assignment_id = p_assignment_id
          AND a.institution_id = p_institution_id
          AND a.revoked_at IS NULL
        FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Teaching assignment not found' USING ERRCODE = 'P0002';
        END IF;
        IF p_actor_user_id = target_faculty THEN
            RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501';
        END IF;
    ELSE
        target_faculty := p_faculty_user_id;
        target_section := p_section_id;
    END IF;

    SELECT c.department_id, co.program_id, co.academic_year_id, co.semester_id,
           s.code, c.course_id
    INTO target_department, target_program, target_year, target_semester,
         target_section_code, target_course
    FROM public.sections AS s
    JOIN public.course_offerings AS co ON co.course_offering_id = s.course_offering_id
    JOIN public.courses AS c ON c.course_id = co.course_id
    JOIN public.departments AS d ON d.department_id = c.department_id
    JOIN public.programs AS prog ON prog.program_id = co.program_id
    JOIN public.departments AS pd ON pd.department_id = prog.department_id
    JOIN public.semesters AS sem ON sem.semester_id = co.semester_id
    JOIN public.academic_years AS ay ON ay.academic_year_id = co.academic_year_id
    WHERE s.section_id = target_section
      AND d.institution_id = p_institution_id
      AND pd.institution_id = p_institution_id
      AND ay.institution_id = p_institution_id
      AND sem.academic_year_id = co.academic_year_id
      AND s.is_active AND co.is_active AND c.is_active AND d.is_active
      AND prog.is_active AND pd.is_active AND sem.is_active AND ay.is_active;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active teaching section in the institution required' USING ERRCODE = '23514';
    END IF;

    PERFORM responsibility.responsibility_id
    FROM public.users AS actor
        JOIN public.user_roles AS ur ON ur.user_id = actor.id
        JOIN public.roles AS role ON role.id = ur.role_id
        JOIN public.faculty_responsibilities AS responsibility
          ON responsibility.faculty_user_id = actor.id
         AND responsibility.institution_id = p_institution_id
        JOIN public.responsibility_definitions AS definition
          ON definition.code = responsibility.responsibility_code
         AND definition.is_active
        JOIN public.responsibility_permissions AS mapping
          ON mapping.responsibility_code = definition.code
        JOIN public.permissions AS permission
          ON permission.permission_id = mapping.permission_id
         AND permission.code = 'faculty.assignments.manage'
         AND permission.is_active
        JOIN public.institutions AS institution
          ON institution.institution_id = p_institution_id
         AND institution.status = 'active'
         AND institution.is_active
        WHERE actor.id = p_actor_user_id
          AND actor.status = 'active'
          AND role.name = 'faculty'
          AND role.is_active
          AND ur.scope_type = 'institution'
          AND ur.scope_id = p_institution_id
          AND responsibility.is_active
          AND responsibility.revoked_at IS NULL
          AND responsibility.start_at <= now()
          AND (responsibility.end_at IS NULL OR now() < responsibility.end_at)
          AND CASE responsibility.scope_type
              WHEN 'department' THEN responsibility.department_id = target_department
              WHEN 'program' THEN responsibility.program_id = target_program
              WHEN 'semester' THEN responsibility.program_id = target_program
                  AND responsibility.academic_year_id = target_year
                  AND responsibility.semester_id = target_semester
              WHEN 'section' THEN responsibility.program_id = target_program
                  AND responsibility.academic_year_id = target_year
                  AND responsibility.semester_id = target_semester
                  AND responsibility.section_code = target_section_code
              WHEN 'course' THEN responsibility.department_id = target_department
                  AND responsibility.course_id = target_course
              ELSE false
          END
    LIMIT 1
    FOR SHARE OF responsibility;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active scoped assignment-management responsibility required' USING ERRCODE = '42501';
    END IF;

    IF p_revoke THEN
        UPDATE public.faculty_section_assignments
        SET revoked_at = now(), revoked_by = p_actor_user_id, is_active = false
        WHERE assignment_id = p_assignment_id
        RETURNING assignment_id, to_jsonb(faculty_section_assignments.*)
        INTO result_id, after_row;
        INSERT INTO public.admin_audit_log(
            actor_user_id, institution_id, action, table_name, record_id, record_data, status
        ) VALUES (
            p_actor_user_id, p_institution_id, 'faculty.assignment.revoke',
            'faculty_section_assignments', result_id::text,
            jsonb_build_object('before', before_row, 'after', after_row), 'success'
        );
        RETURN result_id;
    END IF;

    IF p_start_at IS NULL OR (p_end_at IS NOT NULL AND p_end_at <= p_start_at) THEN
        RAISE EXCEPTION 'Invalid teaching validity interval' USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users AS faculty
        JOIN public.user_roles AS ur ON ur.user_id = faculty.id
        JOIN public.roles AS role ON role.id = ur.role_id
        WHERE faculty.id = target_faculty
          AND faculty.status = 'active'
          AND role.name = 'faculty' AND role.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
    ) THEN
        RAISE EXCEPTION 'Active Faculty member in the institution required' USING ERRCODE = '23514';
    END IF;

    IF p_assignment_id IS NULL THEN
        INSERT INTO public.faculty_section_assignments(
            institution_id, faculty_user_id, section_id, assigned_by,
            start_at, end_at, is_active
        ) VALUES (
            p_institution_id, target_faculty, target_section, p_actor_user_id,
            p_start_at, p_end_at, p_is_active
        )
        RETURNING assignment_id, to_jsonb(faculty_section_assignments.*)
        INTO result_id, after_row;
        INSERT INTO public.admin_audit_log(
            actor_user_id, institution_id, action, table_name, record_id, record_data, status
        ) VALUES (
            p_actor_user_id, p_institution_id, 'faculty.assignment.assign',
            'faculty_section_assignments', result_id::text,
            jsonb_build_object('before', NULL, 'after', after_row), 'success'
        );
    ELSE
        UPDATE public.faculty_section_assignments
        SET start_at = p_start_at, end_at = p_end_at, is_active = p_is_active
        WHERE assignment_id = p_assignment_id
        RETURNING assignment_id, to_jsonb(faculty_section_assignments.*)
        INTO result_id, after_row;
        INSERT INTO public.admin_audit_log(
            actor_user_id, institution_id, action, table_name, record_id, record_data, status
        ) VALUES (
            p_actor_user_id, p_institution_id, 'faculty.assignment.update',
            'faculty_section_assignments', result_id::text,
            jsonb_build_object('before', before_row, 'after', after_row), 'success'
        );
    END IF;
    RETURN result_id;
END;
$$;


ALTER FUNCTION "public"."manage_scoped_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_revoke" boolean) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mark_faculty_attendance"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_session_date" "date", "p_attendance" "jsonb", "p_notes" "text" DEFAULT NULL::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE ctx jsonb; session public.faculty_attendance_sessions; entry record;
    roster public.faculty_attendance_rosters; corrected boolean; linked_count integer := 0;
BEGIN
    ctx := assert_faculty_attendance_mutation(p_actor, p_tenant, p_section_id);
    IF jsonb_typeof(p_attendance) <> 'object' OR p_attendance = '{}'::jsonb
        OR (SELECT count(*) FROM jsonb_object_keys(p_attendance)) > 500 OR length(p_notes) > 2000 THEN
        RAISE EXCEPTION 'Invalid attendance payload' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO session FROM faculty_attendance_sessions
      WHERE section_id = p_section_id AND session_date = p_session_date FOR UPDATE;
    corrected := session.session_id IS NOT NULL;
    IF corrected AND session.conducted_by <> p_actor THEN
        RAISE EXCEPTION 'Session belongs to another teacher' USING ERRCODE = '42501';
    END IF;
    IF NOT corrected THEN
        INSERT INTO faculty_attendance_sessions(institution_id, section_id, course_offering_id, session_date, conducted_by)
        VALUES(p_tenant, p_section_id, (ctx->>'course_offering_id')::uuid, p_session_date, p_actor) RETURNING * INTO session;
        INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
        VALUES(p_actor, p_tenant, 'attendance.session.create', 'faculty_attendance_sessions', session.session_id::text,
            jsonb_build_object('section_id', p_section_id, 'date', p_session_date), 'success');
    END IF;
    FOR entry IN SELECT * FROM jsonb_each_text(p_attendance) LOOP
        IF entry.value NOT IN ('present','absent','late','excused') THEN
            RAISE EXCEPTION 'Invalid attendance status' USING ERRCODE = '23514';
        END IF;
        SELECT * INTO roster FROM faculty_attendance_rosters WHERE roster_id = entry.key::uuid
          AND institution_id = p_tenant AND section_id = p_section_id FOR UPDATE;
        IF roster.roster_id IS NULL THEN RAISE EXCEPTION 'Student scope denied' USING ERRCODE = '42501'; END IF;
        INSERT INTO faculty_attendance_records(session_id, roster_id, status, notes)
        VALUES(session.session_id, roster.roster_id, entry.value, p_notes)
        ON CONFLICT(session_id, roster_id) DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes;
        IF roster.linked_student_id IS NOT NULL AND roster.reconciliation_state <> 'CONFLICT' THEN
            INSERT INTO student_attendance(student_id, institution_id, section_id, academic_year_id, semester_id, date, status, notes)
            VALUES(roster.linked_student_id, p_tenant, p_section_id, (ctx->>'academic_year_id')::uuid,
                (ctx->>'semester_id')::uuid, p_session_date, entry.value, p_notes)
            ON CONFLICT(student_id, section_id, date) DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes;
            linked_count := linked_count + 1;
        END IF;
    END LOOP;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, CASE WHEN corrected THEN 'attendance.session.correct' ELSE 'attendance.session.mark' END,
        'faculty_attendance_sessions', session.session_id::text,
        jsonb_build_object('record_count', (SELECT count(*) FROM jsonb_object_keys(p_attendance))), 'success');
    RETURN jsonb_build_object('session_id', session.session_id, 'record_count', (SELECT count(*) FROM jsonb_object_keys(p_attendance)),
        'updated_existing_student_records', linked_count, 'corrected', corrected);
END; $$;


ALTER FUNCTION "public"."mark_faculty_attendance"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_session_date" "date", "p_attendance" "jsonb", "p_notes" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase613_assert_child_organization"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    institution_organization_id uuid;
BEGIN
    SELECT "i"."organization_id"
        INTO institution_organization_id
        FROM "public"."institutions" AS "i"
        WHERE "i"."institution_id" = NEW."institution_id";

    IF institution_organization_id IS NULL THEN
        RAISE EXCEPTION 'Phase 6.13: institution % does not exist', NEW."institution_id"
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF NEW."organization_id" IS DISTINCT FROM institution_organization_id THEN
        RAISE EXCEPTION
            'Phase 6.13: organization % does not own institution % (expected %)',
            NEW."organization_id", NEW."institution_id", institution_organization_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase613_assert_child_organization"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase613_assert_role_scope"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    institution_organization_id uuid;
BEGIN
    IF NEW."scope_type" <> 'institution'::text THEN
        RETURN NEW;
    END IF;

    SELECT "i"."organization_id"
        INTO institution_organization_id
        FROM "public"."institutions" AS "i"
        WHERE "i"."institution_id" = NEW."scope_id";

    IF institution_organization_id IS NULL
       OR institution_organization_id IS DISTINCT FROM NEW."scope_organization_id" THEN
        RAISE EXCEPTION
            'Phase 6.13: institution scope % is not inside organization scope %',
            NEW."scope_id", NEW."scope_organization_id"
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase613_assert_role_scope"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase613_sync_institution_status"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    IF NEW."status" IS NULL THEN
        NEW."status" := CASE WHEN NEW."is_active" IS TRUE THEN 'active' ELSE 'suspended' END;
    END IF;

    -- status is authoritative: only 'active' means the institution is usable.
    IF NEW."status" = 'active' THEN
        NEW."is_active" := true;
    ELSE
        NEW."is_active" := false;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase613_sync_institution_status"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase712_assert_super_admin_scope"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
DECLARE
    role_name text;
BEGIN
    SELECT "r"."name"
      INTO role_name
      FROM "public"."roles" AS "r"
     WHERE "r"."id" = NEW."role_id";

    IF role_name = 'super_admin'
       AND (
           NEW."scope_type" <> 'platform'
           OR NEW."scope_id" IS NOT NULL
           OR NEW."scope_organization_id" IS NOT NULL
       ) THEN
        RAISE EXCEPTION 'Phase 7.12: super_admin requires platform scope'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase712_assert_super_admin_scope"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase712_assign_super_admin"("p_target_email" "text", "p_actor_identifier" "text") RETURNS TABLE("result" "text", "target_user_id" "uuid")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    target_record "public"."users"%ROWTYPE;
    super_admin_role "public"."roles"%ROWTYPE;
    grant_exists boolean;
    operation_result text;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.12: service role required' USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF "btrim"(COALESCE("p_actor_identifier", '')) = ''
       OR "length"("p_actor_identifier") > 200 THEN
        RAISE EXCEPTION 'Phase 7.12: a bounded actor identifier is required'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO target_record
      FROM "public"."users"
     WHERE "email" = "lower"("btrim"("p_target_email"));
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: target application user not found'
            USING ERRCODE = 'no_data_found';
    END IF;
    IF target_record."status" <> 'active' THEN
        RAISE EXCEPTION 'Phase 7.12: target application user is not active'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO super_admin_role
      FROM "public"."roles"
     WHERE "name" = 'super_admin' AND "is_active" = true;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: active super_admin role is unavailable'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM "public"."user_roles"
         WHERE "user_id" = target_record."id"
           AND "role_id" = super_admin_role."id"
    ) INTO grant_exists;

    INSERT INTO "public"."user_roles" (
        "user_id", "role_id", "scope_type", "scope_id", "scope_organization_id"
    ) VALUES (
        target_record."id", super_admin_role."id", 'platform', NULL, NULL
    )
    ON CONFLICT ("user_id", "role_id") DO UPDATE
       SET "scope_type" = 'platform',
           "scope_id" = NULL,
           "scope_organization_id" = NULL;

    operation_result := CASE WHEN grant_exists THEN 'already_assigned' ELSE 'assigned' END;
    INSERT INTO "public"."platform_role_audit_log" (
        "actor_identifier", "action", "target_user_id", "role_name", "result", "metadata"
    ) VALUES (
        "btrim"("p_actor_identifier"), 'assign', target_record."id", 'super_admin',
        operation_result, '{"scope":"platform"}'::jsonb
    );

    RETURN QUERY SELECT operation_result, target_record."id";
END;
$$;


ALTER FUNCTION "public"."phase712_assign_super_admin"("p_target_email" "text", "p_actor_identifier" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase712_revoke_super_admin"("p_target_email" "text", "p_actor_identifier" "text") RETURNS TABLE("result" "text", "target_user_id" "uuid")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    target_record "public"."users"%ROWTYPE;
    super_admin_role_id uuid;
    removed_count integer;
    operation_result text;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.12: service role required' USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF "btrim"(COALESCE("p_actor_identifier", '')) = ''
       OR "length"("p_actor_identifier") > 200 THEN
        RAISE EXCEPTION 'Phase 7.12: a bounded actor identifier is required'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO target_record
      FROM "public"."users"
     WHERE "email" = "lower"("btrim"("p_target_email"));
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: target application user not found'
            USING ERRCODE = 'no_data_found';
    END IF;

    SELECT "id" INTO super_admin_role_id
      FROM "public"."roles"
     WHERE "name" = 'super_admin';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: super_admin role is unavailable'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    DELETE FROM "public"."user_roles"
     WHERE "user_id" = target_record."id"
       AND "role_id" = super_admin_role_id;
    GET DIAGNOSTICS removed_count = ROW_COUNT;

    operation_result := CASE WHEN removed_count = 1 THEN 'revoked' ELSE 'already_revoked' END;
    INSERT INTO "public"."platform_role_audit_log" (
        "actor_identifier", "action", "target_user_id", "role_name", "result", "metadata"
    ) VALUES (
        "btrim"("p_actor_identifier"), 'revoke', target_record."id", 'super_admin',
        operation_result, '{"scope":"platform"}'::jsonb
    );

    RETURN QUERY SELECT operation_result, target_record."id";
END;
$$;


ALTER FUNCTION "public"."phase712_revoke_super_admin"("p_target_email" "text", "p_actor_identifier" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase714_assert_invitation_transition"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
    IF NEW."status" IS DISTINCT FROM OLD."status" THEN
        IF OLD."status" <> 'invited'::text THEN
            RAISE EXCEPTION 'Phase 7.14: invitation % is already terminal', OLD."status"
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW."status" NOT IN ('accepted'::text, 'cancelled'::text, 'expired'::text) THEN
            RAISE EXCEPTION 'Phase 7.14: invalid invitation transition'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- The binding of an invitation is immutable: an invitation can never be
    -- re-pointed at another institution, another email, or another role.
    IF NEW."institution_id" IS DISTINCT FROM OLD."institution_id"
       OR NEW."role_name" IS DISTINCT FROM OLD."role_name"
       OR NEW."token_hash" IS DISTINCT FROM OLD."token_hash"
       OR NEW."email" IS DISTINCT FROM OLD."email"
       OR NEW."created_by" IS DISTINCT FROM OLD."created_by"
       OR NEW."expires_at" IS DISTINCT FROM OLD."expires_at"
       OR NEW."created_at" IS DISTINCT FROM OLD."created_at" THEN
        RAISE EXCEPTION 'Phase 7.14: invitation identity is immutable'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase714_assert_invitation_transition"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase715_assert_invitation_transition"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
    IF NEW."status" IS DISTINCT FROM OLD."status" THEN
        IF OLD."status" <> 'invited'::text THEN
            RAISE EXCEPTION 'Phase 7.15: invitation % is already terminal', OLD."status"
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW."status" NOT IN ('accepted'::text, 'cancelled'::text, 'expired'::text) THEN
            RAISE EXCEPTION 'Phase 7.15: invalid invitation transition'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- The invitation's BINDING is immutable for its whole life: the tenant, the
    -- role, the invited person and the issuing Super Admin never change, and
    -- neither does the creation timestamp.
    IF NEW."institution_id" IS DISTINCT FROM OLD."institution_id"
       OR NEW."role_name" IS DISTINCT FROM OLD."role_name"
       OR NEW."email" IS DISTINCT FROM OLD."email"
       OR NEW."created_by" IS DISTINCT FROM OLD."created_by"
       OR NEW."created_at" IS DISTINCT FROM OLD."created_at" THEN
        RAISE EXCEPTION 'Phase 7.15: invitation identity is immutable'
            USING ERRCODE = 'check_violation';
    END IF;

    -- Token rotation is permitted ONLY while the invitation is still pending
    -- AND the row is not transitioning to a terminal state in the same
    -- statement. A terminal invitation keeps its digest forever, so a
    -- superseded, consumed, cancelled or expired token can never be revived.
    IF (NEW."token_hash" IS DISTINCT FROM OLD."token_hash"
        OR NEW."expires_at" IS DISTINCT FROM OLD."expires_at") THEN
        IF OLD."status" <> 'invited'::text
           OR NEW."status" IS DISTINCT FROM OLD."status" THEN
            RAISE EXCEPTION 'Phase 7.15: only a pending invitation token may be rotated'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Verification may only be recorded on an already-accepted row (enforced
    -- again here so the invariant holds even if the CHECK is ever dropped),
    -- and it may never be un-recorded.
    IF OLD."email_verified_at" IS NOT NULL
       AND NEW."email_verified_at" IS DISTINCT FROM OLD."email_verified_at" THEN
        RAISE EXCEPTION 'Phase 7.15: email verification is irreversible'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase715_assert_invitation_transition"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase717_cancel_terminal_invitation_email"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
    IF NEW."status" <> 'invited'::text AND OLD."status" = 'invited'::text THEN
        UPDATE "public"."email_outbox"
        SET "status" = 'cancelled'::text, "locked_at" = NULL,
            "protected_token" = NULL, "updated_at" = now(),
            "last_error_category" = 'INVITATION_TERMINAL'::text
        WHERE "aggregate_id" = NEW."invitation_id"
          AND "status" = 'pending'::text;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."phase717_cancel_terminal_invitation_email"() OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."email_outbox" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "message_type" "text" DEFAULT 'admin_invitation'::"text" NOT NULL,
    "aggregate_type" "text" DEFAULT 'platform_admin_invitation'::"text" NOT NULL,
    "aggregate_id" "uuid" NOT NULL,
    "protected_token" "text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "attempt_count" integer DEFAULT 0 NOT NULL,
    "available_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "locked_at" timestamp with time zone,
    "sent_at" timestamp with time zone,
    "failed_at" timestamp with time zone,
    "delivery_updated_at" timestamp with time zone,
    "provider_name" "text",
    "provider_message_id" "text",
    "last_error_category" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "delivery_sequence" bigint NOT NULL,
    CONSTRAINT "email_outbox_aggregate_type_check" CHECK (("aggregate_type" = 'platform_admin_invitation'::"text")),
    CONSTRAINT "email_outbox_attempt_count_check" CHECK (("attempt_count" >= 0)),
    CONSTRAINT "email_outbox_message_type_check" CHECK (("message_type" = 'admin_invitation'::"text")),
    CONSTRAINT "email_outbox_processing_lock_check" CHECK (((("status" = 'processing'::"text") AND ("locked_at" IS NOT NULL)) OR (("status" <> 'processing'::"text") AND ("locked_at" IS NULL)))),
    CONSTRAINT "email_outbox_protected_token_check" CHECK (((("status" = ANY (ARRAY['pending'::"text", 'processing'::"text"])) AND ("protected_token" IS NOT NULL) AND ("length"("btrim"("protected_token")) >= 80)) OR (("status" <> ALL (ARRAY['pending'::"text", 'processing'::"text"])) AND ("protected_token" IS NULL)))),
    CONSTRAINT "email_outbox_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'sent'::"text", 'delivered'::"text", 'bounced'::"text", 'complained'::"text", 'dead_letter'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "public"."email_outbox" OWNER TO "postgres";


COMMENT ON COLUMN "public"."email_outbox"."protected_token" IS 'Authenticated ciphertext needed to render the one-time URL. Never plaintext; key remains backend-only.';



CREATE OR REPLACE FUNCTION "public"."phase717_claim_email_outbox"("p_batch_size" integer, "p_lock_seconds" integer, "p_retry_limit" integer) RETURNS SETOF "public"."email_outbox"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
BEGIN
    -- Jobs whose invitation is terminal or elapsed cannot produce a usable
    -- URL and must not remain pending forever.
    UPDATE "public"."email_outbox" AS o
    SET "status" = 'cancelled'::text, "protected_token" = NULL,
        "updated_at" = now(),
        "last_error_category" = 'INVITATION_NOT_DELIVERABLE'::text
    FROM "public"."platform_admin_invitations" AS i
    WHERE i."invitation_id" = o."aggregate_id"
      AND o."status" = 'pending'::text
      AND (i."status" <> 'invited'::text OR i."expires_at" <= now());

    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = CASE WHEN o."attempt_count" >= p_retry_limit
                        THEN 'dead_letter'::text ELSE 'retry'::text END,
        "completed_at" = now(), "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id" AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'dead_letter'::text, "locked_at" = NULL,
        "protected_token" = NULL,
        "failed_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds)
      AND "attempt_count" >= p_retry_limit;

    UPDATE "public"."platform_admin_invitations" AS i
    SET "email_delivery_status" = 'failed'::text,
        "email_delivery_at" = now(), "updated_at" = now()
    FROM "public"."email_outbox" AS o
    WHERE o."aggregate_id" = i."invitation_id"
      AND o."status" = 'dead_letter'::text
      AND o."last_error_category" = 'WORKER_LEASE_EXPIRED'::text;

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds)
      AND "attempt_count" < p_retry_limit;

    RETURN QUERY
    WITH eligible AS (
        SELECT o."id"
        FROM "public"."email_outbox" AS o
        JOIN "public"."platform_admin_invitations" AS i
          ON i."invitation_id" = o."aggregate_id"
        WHERE o."status" = 'pending'::text
          AND o."available_at" <= now()
          AND o."attempt_count" < p_retry_limit
          AND i."status" = 'invited'::text
          AND i."expires_at" > now()
        ORDER BY o."available_at", o."created_at"
        FOR UPDATE OF o SKIP LOCKED
        LIMIT LEAST(GREATEST(p_batch_size, 1), 200)
    ), claimed AS (
        UPDATE "public"."email_outbox" AS o
        SET "status" = 'processing'::text, "locked_at" = now(),
            "attempt_count" = o."attempt_count" + 1, "updated_at" = now()
        FROM eligible AS e WHERE o."id" = e."id"
        RETURNING o.*
    ), attempts AS (
        INSERT INTO "public"."email_delivery_attempts"
            ("outbox_id", "attempt_number", "started_at", "result")
        SELECT c."id", c."attempt_count", now(), 'processing'::text FROM claimed AS c
        RETURNING "outbox_id"
    )
    SELECT c.* FROM claimed AS c JOIN attempts AS a ON a."outbox_id" = c."id";
END;
$$;


ALTER FUNCTION "public"."phase717_claim_email_outbox"("p_batch_size" integer, "p_lock_seconds" integer, "p_retry_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase717_complete_email_outbox"("p_outbox_id" "uuid", "p_attempt_number" integer, "p_outcome" "text", "p_provider_name" "text", "p_provider_message_id" "text" DEFAULT NULL::"text", "p_failure_category" "text" DEFAULT NULL::"text", "p_available_at" timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    v_outbox "public"."email_outbox"%ROWTYPE;
    v_invitation_status text;
BEGIN
    IF p_outcome NOT IN ('sent'::text, 'retry'::text, 'dead_letter'::text, 'cancelled'::text) THEN
        RAISE EXCEPTION 'invalid email outbox outcome' USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO v_outbox FROM "public"."email_outbox"
    WHERE "id" = p_outbox_id FOR UPDATE;
    IF NOT FOUND OR v_outbox."status" <> 'processing'::text
       OR v_outbox."attempt_count" <> p_attempt_number THEN
        RETURN false;
    END IF;

    UPDATE "public"."email_delivery_attempts"
    SET "completed_at" = now(), "result" = p_outcome,
        "failure_category" = p_failure_category,
        "provider_message_id" = p_provider_message_id
    WHERE "outbox_id" = p_outbox_id AND "attempt_number" = p_attempt_number
      AND "result" = 'processing'::text;

    UPDATE "public"."email_outbox"
    SET "status" = CASE WHEN p_outcome = 'retry'::text THEN 'pending'::text
                        ELSE p_outcome END,
        "locked_at" = NULL,
        "available_at" = CASE WHEN p_outcome = 'retry'::text
                              THEN COALESCE(p_available_at, now())
                              ELSE "available_at" END,
        "sent_at" = CASE WHEN p_outcome = 'sent'::text THEN now() ELSE "sent_at" END,
        "failed_at" = CASE WHEN p_outcome = 'dead_letter'::text THEN now() ELSE "failed_at" END,
        "provider_name" = NULLIF(btrim(p_provider_name), ''),
        "provider_message_id" = p_provider_message_id,
        "last_error_category" = p_failure_category,
        "protected_token" = CASE WHEN p_outcome = 'retry'::text
                                 THEN "protected_token" ELSE NULL END,
        "delivery_updated_at" = now(), "updated_at" = now()
    WHERE "id" = p_outbox_id;

    v_invitation_status := CASE
        WHEN p_outcome = 'sent'::text THEN 'sent'::text
        WHEN p_outcome IN ('dead_letter'::text, 'cancelled'::text) THEN 'failed'::text
        ELSE 'pending'::text END;
    UPDATE "public"."platform_admin_invitations"
    SET "email_delivery_status" = v_invitation_status,
        "email_delivery_at" = now(),
        "email_delivery_attempts" = "email_delivery_attempts" + 1,
        "last_sent_at" = CASE WHEN p_outcome = 'sent'::text THEN now()
                              ELSE "last_sent_at" END,
        "updated_at" = now()
    WHERE "invitation_id" = v_outbox."aggregate_id";
    RETURN true;
END;
$$;


ALTER FUNCTION "public"."phase717_complete_email_outbox"("p_outbox_id" "uuid", "p_attempt_number" integer, "p_outcome" "text", "p_provider_name" "text", "p_provider_message_id" "text", "p_failure_category" "text", "p_available_at" timestamp with time zone) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    -- Preserve the prior service behaviour: an elapsed row is terminalized
    -- before issuing a replacement, while a still-live duplicate is rejected
    -- by the partial unique index even under concurrent requests.
    UPDATE "public"."platform_admin_invitations"
    SET "status" = 'expired'::text, "updated_at" = now()
    WHERE "institution_id" = p_institution_id
      AND lower("email") = lower(btrim(p_email))
      AND "status" = 'invited'::text
      AND "expires_at" <= now();

    INSERT INTO "public"."platform_admin_invitations" (
        "institution_id", "email", "token_hash", "role_name", "status",
        "expires_at", "created_by", "email_delivery_status"
    ) VALUES (
        p_institution_id, lower(btrim(p_email)), p_token_hash, 'admin'::text,
        'invited'::text, p_expires_at, p_created_by, 'pending'::text
    ) RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (v_invitation."invitation_id", p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;


ALTER FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text", "p_role_name" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    IF p_role_name NOT IN ('admin', 'staff', 'faculty') THEN
        RAISE EXCEPTION 'unsupported institution invitation role'
            USING ERRCODE = '22023';
    END IF;

    UPDATE "public"."platform_admin_invitations"
    SET "status" = 'expired'::text, "updated_at" = now()
    WHERE "institution_id" = p_institution_id
      AND lower("email") = lower(btrim(p_email))
      AND "status" = 'invited'::text
      AND "expires_at" <= now();

    INSERT INTO "public"."platform_admin_invitations" (
        "institution_id", "email", "token_hash", "role_name", "status",
        "expires_at", "created_by", "email_delivery_status"
    ) VALUES (
        p_institution_id, lower(btrim(p_email)), p_token_hash, p_role_name,
        'invited'::text, p_expires_at, p_created_by, 'pending'::text
    ) RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (v_invitation."invitation_id", p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;


ALTER FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text", "p_role_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase717_resolve_email_outbox_context"("p_outbox_id" "uuid", "p_token_hash" "text") RETURNS "jsonb"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
    SELECT CASE
        WHEN o."status" = 'processing'::text
         AND i."status" = 'invited'::text
         AND i."expires_at" > now()
         AND i."token_hash" = p_token_hash
        THEN jsonb_build_object(
            'invitation_id', i."invitation_id",
            'recipient', i."email",
            'institution_name', n."name",
            'expires_at', i."expires_at",
            'role_name', i."role_name"
        )
        ELSE NULL
    END
    FROM "public"."email_outbox" AS o
    JOIN "public"."platform_admin_invitations" AS i
      ON i."invitation_id" = o."aggregate_id"
    JOIN "public"."institutions" AS n
      ON n."institution_id" = i."institution_id"
    WHERE o."id" = p_outbox_id;
$$;


ALTER FUNCTION "public"."phase717_resolve_email_outbox_context"("p_outbox_id" "uuid", "p_token_hash" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase717_rotate_invitation_with_outbox"("p_invitation_id" "uuid", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_expected_updated_at" timestamp with time zone, "p_protected_token" "text", "p_lock_seconds" integer) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    SELECT * INTO v_invitation
    FROM "public"."platform_admin_invitations"
    WHERE "invitation_id" = p_invitation_id
    FOR UPDATE;

    IF NOT FOUND OR v_invitation."status" <> 'invited'::text
       OR v_invitation."expires_at" <= now()
       OR (p_expected_updated_at IS NOT NULL
           AND v_invitation."updated_at" IS DISTINCT FROM p_expected_updated_at) THEN
        RETURN NULL;
    END IF;

    -- Recover an abandoned lease before deciding whether resend can proceed.
    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = 'retry'::text, "completed_at" = now(),
        "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id"
      AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."aggregate_id" = p_invitation_id
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds);

    -- A non-stale worker may already be inside provider I/O. Refuse the resend
    -- rather than rotate the token underneath that delivery.
    IF EXISTS (
        SELECT 1 FROM "public"."email_outbox"
        WHERE "aggregate_id" = p_invitation_id
          AND "status" = 'processing'::text
    ) THEN
        RETURN NULL;
    END IF;

    UPDATE "public"."email_outbox"
    SET "status" = 'cancelled'::text, "locked_at" = NULL,
        "protected_token" = NULL, "updated_at" = now(),
        "last_error_category" = 'INVITATION_SUPERSEDED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'pending'::text;

    UPDATE "public"."platform_admin_invitations"
    SET "token_hash" = p_token_hash, "expires_at" = p_expires_at,
        "resend_count" = "resend_count" + 1,
        "email_delivery_status" = 'pending'::text,
        "email_delivery_at" = NULL, "updated_at" = now()
    WHERE "invitation_id" = p_invitation_id
    RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (p_invitation_id, p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;


ALTER FUNCTION "public"."phase717_rotate_invitation_with_outbox"("p_invitation_id" "uuid", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_expected_updated_at" timestamp with time zone, "p_protected_token" "text", "p_lock_seconds" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase718_reconcile_mailgun_event"("p_event_key" "text", "p_replay_token_digest" "text", "p_provider_event_id" "text", "p_provider_message_id" "text", "p_event_type" "text", "p_event_timestamp" timestamp with time zone) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    v_event_id uuid;
    v_outbox "public"."email_outbox"%ROWTYPE;
    v_new_status text;
    v_result text;
    v_changed boolean := false;
    v_is_latest boolean := false;
BEGIN
    IF length(p_event_key) <> 64 OR length(p_replay_token_digest) <> 64
       OR NULLIF(btrim(p_provider_event_id), '') IS NULL
       OR p_event_timestamp IS NULL THEN
        RAISE EXCEPTION 'invalid verified email event' USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO "public"."email_delivery_events" (
        "provider_name", "event_key", "replay_token_digest",
        "provider_event_id", "provider_message_id", "event_type",
        "event_timestamp"
    ) VALUES (
        'mailgun'::text, p_event_key, p_replay_token_digest,
        p_provider_event_id, NULLIF(btrim(p_provider_message_id), ''),
        p_event_type, p_event_timestamp
    ) ON CONFLICT DO NOTHING
    RETURNING "id" INTO v_event_id;

    IF v_event_id IS NULL THEN
        RETURN jsonb_build_object(
            'result', 'duplicate', 'state_changed', false
        );
    END IF;

    IF p_event_type = 'unsupported'::text THEN
        UPDATE "public"."email_delivery_events"
        SET "processing_result" = 'unsupported'::text, "processed_at" = now()
        WHERE "id" = v_event_id;
        RETURN jsonb_build_object(
            'result', 'unsupported', 'state_changed', false
        );
    END IF;

    SELECT * INTO v_outbox
    FROM "public"."email_outbox"
    WHERE "provider_name" = 'mailgun'::text
      AND "provider_message_id" = NULLIF(btrim(p_provider_message_id), '')
    FOR UPDATE;

    IF NOT FOUND THEN
        UPDATE "public"."email_delivery_events"
        SET "processing_result" = 'unknown_message'::text, "processed_at" = now()
        WHERE "id" = v_event_id;
        RETURN jsonb_build_object(
            'result', 'unknown_message', 'state_changed', false
        );
    END IF;

    UPDATE "public"."email_delivery_events"
    SET "outbox_id" = v_outbox."id"
    WHERE "id" = v_event_id;

    SELECT NOT EXISTS (
        SELECT 1 FROM "public"."email_outbox" AS newer
        WHERE newer."aggregate_id" = v_outbox."aggregate_id"
          AND newer."delivery_sequence" > v_outbox."delivery_sequence"
    ) INTO v_is_latest;

    v_new_status := v_outbox."status";
    IF p_event_type = 'delivered'::text AND v_outbox."status" = 'sent'::text THEN
        v_new_status := 'delivered'::text;
    ELSIF p_event_type IN ('permanent_failure'::text, 'rejected'::text)
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        v_new_status := 'bounced'::text;
    ELSIF p_event_type = 'complained'::text
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        v_new_status := 'complained'::text;
    END IF;

    v_changed := v_new_status IS DISTINCT FROM v_outbox."status";
    IF v_changed THEN
        UPDATE "public"."email_outbox"
        SET "status" = v_new_status,
            "last_error_category" = CASE
                WHEN p_event_type = 'temporary_failure'::text
                    THEN 'MAILGUN_TEMPORARY_FAILURE'::text
                WHEN p_event_type IN ('permanent_failure'::text, 'rejected'::text)
                    THEN 'MAILGUN_PERMANENT_FAILURE'::text
                WHEN p_event_type = 'complained'::text
                    THEN 'MAILGUN_COMPLAINT'::text
                ELSE "last_error_category" END,
            "delivery_updated_at" = p_event_timestamp,
            "updated_at" = now()
        WHERE "id" = v_outbox."id";
    ELSIF p_event_type = 'temporary_failure'::text
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        UPDATE "public"."email_outbox"
        SET "last_error_category" = 'MAILGUN_TEMPORARY_FAILURE'::text,
            "delivery_updated_at" = p_event_timestamp, "updated_at" = now()
        WHERE "id" = v_outbox."id";
    END IF;

    -- An event for an older send is retained on that outbox row but cannot
    -- overwrite the invitation projection for a newer resend generation.
    IF v_is_latest AND v_changed THEN
        UPDATE "public"."platform_admin_invitations"
        SET "email_delivery_status" = CASE
                WHEN v_new_status = 'delivered'::text THEN 'delivered'::text
                ELSE 'failed'::text END,
            "email_delivery_at" = p_event_timestamp,
            "updated_at" = now()
        WHERE "invitation_id" = v_outbox."aggregate_id";
    END IF;

    v_result := CASE
        WHEN NOT v_is_latest THEN 'stale_generation'::text
        WHEN v_changed THEN 'applied'::text
        ELSE 'no_state_change'::text END;
    UPDATE "public"."email_delivery_events"
    SET "processing_result" = v_result, "state_changed" = v_changed,
        "processed_at" = now()
    WHERE "id" = v_event_id;

    RETURN jsonb_build_object(
        'result', v_result,
        'state_changed', v_changed,
        'outbox_id', v_outbox."id"
    );
END;
$$;


ALTER FUNCTION "public"."phase718_reconcile_mailgun_event"("p_event_key" "text", "p_replay_token_digest" "text", "p_provider_event_id" "text", "p_provider_message_id" "text", "p_event_type" "text", "p_event_timestamp" timestamp with time zone) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_and_grant_role"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    "v_request" "public"."institution_membership_requests"%ROWTYPE;
    "v_role_id" uuid;
    "v_previous_scope_type" text;
    "v_previous_scope_id" uuid;
    "v_changed" boolean := false;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.24: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT * INTO "v_request"
      FROM "public"."institution_membership_requests"
     WHERE "request_id" = "p_request_id"
       AND "institution_id" = "p_institution_id"
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN "jsonb_build_object"('not_found', true);
    END IF;
    IF "v_request"."status" = 'approved'::text THEN
        RETURN "jsonb_build_object"('already_applied', true);
    END IF;
    IF "v_request"."status" <> 'pending'::text THEN
        RETURN "jsonb_build_object"('conflict', true);
    END IF;
    IF "v_request"."requested_role" NOT IN ('staff', 'faculty') THEN
        RETURN "jsonb_build_object"('invalid_role', true);
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."institutions" AS "institution"
          JOIN "public"."users" AS "applicant"
            ON "applicant"."id" = "v_request"."user_id"
         WHERE "institution"."institution_id" = "p_institution_id"
           AND "institution"."organization_id" = "v_request"."organization_id"
           AND "institution"."status" = 'active'::text
           AND "institution"."is_active" = true
           AND "lower"("applicant"."email") = "lower"("v_request"."official_email")
           AND "applicant"."status" = 'active'::text
    ) THEN
        RETURN "jsonb_build_object"('invalid_state', true);
    END IF;

    PERFORM "public"."phase81_assert_institution_admin"(
        "p_decided_by", "p_institution_id"
    );

    SELECT "id" INTO "v_role_id"
      FROM "public"."roles"
     WHERE "name" = "v_request"."requested_role"
       AND "is_active" = true;
    IF "v_role_id" IS NULL THEN
        RETURN "jsonb_build_object"('role_not_configured', true);
    END IF;

    SELECT "scope_type", "scope_id"
      INTO "v_previous_scope_type", "v_previous_scope_id"
      FROM "public"."user_roles"
     WHERE "user_id" = "v_request"."user_id"
       AND "role_id" = "v_role_id"
     FOR UPDATE;
    "v_changed" := NOT FOUND
        OR "v_previous_scope_type" IS DISTINCT FROM 'institution'
        OR "v_previous_scope_id" IS DISTINCT FROM "p_institution_id";

    INSERT INTO "public"."user_roles" (
        "user_id", "role_id", "scope_type", "scope_id", "scope_organization_id"
    ) VALUES (
        "v_request"."user_id", "v_role_id", 'institution'::text,
        "p_institution_id", "v_request"."organization_id"
    )
    ON CONFLICT ("user_id", "role_id") DO UPDATE
        SET "scope_type" = EXCLUDED."scope_type",
            "scope_id" = EXCLUDED."scope_id",
            "scope_organization_id" = EXCLUDED."scope_organization_id";

    IF "v_changed" THEN
        INSERT INTO "public"."admin_audit_log" (
            "actor_user_id", "institution_id", "action", "table_name",
            "record_id", "record_data", "status"
        ) VALUES (
            "p_decided_by", "p_institution_id", 'role.assignment',
            'user_roles', "v_request"."user_id"::text,
            "jsonb_build_object"(
                'role', "v_request"."requested_role",
                'institution_id', "p_institution_id",
                'membership_request_id', "p_request_id"
            ),
            'success'
        );
    END IF;

    UPDATE "public"."institution_membership_requests"
       SET "status" = 'approved'::text,
           "decided_by_user_id" = "p_decided_by",
           "decided_at" = "now"(),
           "decision_reason" = "p_reason",
           "updated_at" = "now"()
     WHERE "request_id" = "p_request_id";

    RETURN "jsonb_build_object"(
        'already_applied', false,
        'role_granted', true
    );
END;
$$;


ALTER FUNCTION "public"."phase723_approve_membership_and_grant_role"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_with_invitation"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_protected_token" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    v_request "public"."institution_membership_requests"%ROWTYPE;
    v_invitation jsonb;
BEGIN
    SELECT * INTO v_request
    FROM "public"."institution_membership_requests"
    WHERE "request_id" = p_request_id
      AND "institution_id" = p_institution_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('not_found', true);
    END IF;
    IF v_request."status" = 'approved'::text THEN
        RETURN jsonb_build_object('already_applied', true);
    END IF;
    IF v_request."status" <> 'pending'::text THEN
        RETURN jsonb_build_object('conflict', true);
    END IF;
    IF v_request."requested_role" NOT IN ('staff', 'faculty') THEN
        RETURN jsonb_build_object('invalid_role', true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "public"."institutions" AS i
        WHERE i."institution_id" = p_institution_id
          AND i."status" = 'active'::text AND i."is_active" = true
          AND i."organization_id" = v_request."organization_id"
    ) OR NOT EXISTS (
        SELECT 1 FROM "public"."users" AS u
        WHERE u."id" = v_request."user_id"
          AND lower(u."email") = lower(v_request."official_email")
          AND u."status" = 'active'::text
    ) THEN
        RETURN jsonb_build_object('invalid_state', true);
    END IF;

    SELECT "public"."phase717_create_invitation_with_outbox"(
        p_institution_id, v_request."official_email", p_token_hash,
        p_expires_at, p_decided_by, p_protected_token,
        v_request."requested_role"
    ) INTO v_invitation;

    UPDATE "public"."institution_membership_requests"
    SET "status" = 'approved'::text,
        "decided_by_user_id" = p_decided_by,
        "decided_at" = now(),
        "decision_reason" = p_reason,
        "updated_at" = now()
    WHERE "request_id" = p_request_id;

    RETURN v_invitation || jsonb_build_object('already_applied', false);
END;
$$;


ALTER FUNCTION "public"."phase723_approve_membership_with_invitation"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_protected_token" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase81_assert_institution_admin"("p_actor_user_id" "uuid", "p_institution_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 8.1: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."users" AS "actor"
          JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "actor"."id"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
          JOIN "public"."institutions" AS "i" ON "i"."institution_id" = "p_institution_id"
         WHERE "actor"."id" = "p_actor_user_id"
           AND "actor"."status" = 'active'
           AND "r"."name" = 'admin'
           AND "r"."is_active" = true
           AND "ur"."scope_type" = 'institution'
           AND "ur"."scope_id" = "p_institution_id"
           AND "i"."status" = 'active'
           AND "i"."is_active" = true
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active institution administrator required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
END;
$$;


ALTER FUNCTION "public"."phase81_assert_institution_admin"("p_actor_user_id" "uuid", "p_institution_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase81_assign_institution_role_audited"("p_actor_user_id" "uuid", "p_target_user_id" "uuid", "p_institution_id" "uuid", "p_role_name" "text") RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    "role_id" uuid;
    "organization_id" uuid;
    "previous_scope_type" text;
    "previous_scope_id" uuid;
    "changed" boolean := false;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 8.1: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF "p_role_name" NOT IN ('admin', 'staff', 'faculty') THEN
        RAISE EXCEPTION 'Phase 8.1: unsupported institution role'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "public"."users"
         WHERE "id" = "p_target_user_id" AND "status" = 'active'
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active target account required'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "public"."institutions"
         WHERE "institution_id" = "p_institution_id"
           AND "status" = 'active' AND "is_active" = true
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active institution required'
            USING ERRCODE = 'check_violation';
    END IF;
    IF "p_actor_user_id" <> "p_target_user_id" AND NOT EXISTS (
        SELECT 1
          FROM "public"."users" AS "actor"
          JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "actor"."id"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
         WHERE "actor"."id" = "p_actor_user_id"
           AND "actor"."status" = 'active'
           AND "r"."name" = 'super_admin' AND "r"."is_active" = true
           AND "ur"."scope_type" = 'platform'
           AND "ur"."scope_id" IS NULL
           AND "ur"."scope_organization_id" IS NULL
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: target acceptance or active platform administrator required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT "institution"."organization_id" INTO "organization_id"
      FROM "public"."institutions" AS "institution"
     WHERE "institution"."institution_id" = "p_institution_id";
    SELECT "id" INTO "role_id"
      FROM "public"."roles"
     WHERE "name" = "p_role_name" AND "is_active" = true;
    IF "role_id" IS NULL OR "organization_id" IS NULL THEN
        RAISE EXCEPTION 'Phase 8.1: role or organization scope is not configured'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT "ur"."scope_type", "ur"."scope_id"
      INTO "previous_scope_type", "previous_scope_id"
      FROM "public"."user_roles" AS "ur"
     WHERE "ur"."user_id" = "p_target_user_id" AND "ur"."role_id" = "role_id"
     FOR UPDATE;
    "changed" := NOT FOUND OR "previous_scope_type" IS DISTINCT FROM 'institution'
        OR "previous_scope_id" IS DISTINCT FROM "p_institution_id";

    INSERT INTO "public"."user_roles"
        ("user_id", "role_id", "scope_type", "scope_id", "scope_organization_id")
    VALUES
        ("p_target_user_id", "role_id", 'institution', "p_institution_id", "organization_id")
    ON CONFLICT ("user_id", "role_id") DO UPDATE
        SET "scope_type" = EXCLUDED."scope_type",
            "scope_id" = EXCLUDED."scope_id",
            "scope_organization_id" = EXCLUDED."scope_organization_id";

    IF "changed" THEN
        INSERT INTO "public"."admin_audit_log"
            ("actor_user_id", "institution_id", "action", "table_name",
             "record_id", "record_data", "status")
        VALUES
            ("p_actor_user_id", "p_institution_id", 'role.assignment',
             'user_roles', "p_target_user_id"::text,
             "jsonb_build_object"('role', "p_role_name",
                 'institution_id', "p_institution_id"), 'success');
    END IF;
    RETURN "changed";
END;
$$;


ALTER FUNCTION "public"."phase81_assign_institution_role_audited"("p_actor_user_id" "uuid", "p_target_user_id" "uuid", "p_institution_id" "uuid", "p_role_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase81_manage_faculty_section_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean DEFAULT false) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    IF p_actor_user_id = p_faculty_user_id OR NOT EXISTS (
        SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id JOIN public.permissions p ON p.permission_id = rp.permission_id
        WHERE ur.user_id = p_actor_user_id AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND r.name = 'admin' AND r.is_active AND p.code = 'faculty.assignments.manage' AND p.is_active
    ) THEN RAISE EXCEPTION 'Assignment authority denied' USING ERRCODE = '42501'; END IF;
    IF NOT p_revoke AND NOT EXISTS (
        SELECT 1 FROM public.sections s JOIN public.course_offerings co USING(course_offering_id)
        JOIN public.courses c USING(course_id) JOIN public.departments d ON d.department_id=c.department_id
        JOIN public.programs prog ON prog.program_id=co.program_id
        JOIN public.departments pd ON pd.department_id=prog.department_id
        JOIN public.semesters sem ON sem.semester_id=co.semester_id
        JOIN public.academic_years ay ON ay.academic_year_id=co.academic_year_id
        WHERE s.section_id=p_section_id AND s.is_active AND co.is_active AND c.is_active AND d.is_active
          AND prog.is_active AND pd.is_active AND sem.is_active AND ay.is_active
          AND d.institution_id=p_institution_id AND pd.institution_id=p_institution_id AND ay.institution_id=p_institution_id
          AND sem.academic_year_id=co.academic_year_id
    ) THEN RAISE EXCEPTION 'Active teaching academic scope required' USING ERRCODE = '23514'; END IF;
    RETURN public.phase81_manage_faculty_section_assignment_original(
        p_actor_user_id, p_institution_id, p_faculty_user_id, p_section_id, p_revoke);
END; $$;


ALTER FUNCTION "public"."phase81_manage_faculty_section_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase81_manage_faculty_section_assignment_original"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean DEFAULT false) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    "assignment_id" uuid;
BEGIN
    PERFORM "public"."phase81_assert_institution_admin"(
        "p_actor_user_id", "p_institution_id"
    );
    IF NOT "p_revoke" THEN
        IF NOT EXISTS (
            SELECT 1
              FROM "public"."users" AS "faculty"
              JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "faculty"."id"
              JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
             WHERE "faculty"."id" = "p_faculty_user_id"
               AND "faculty"."status" = 'active'
               AND "r"."name" = 'faculty'
               AND "r"."is_active" = true
               AND "ur"."scope_type" = 'institution'
               AND "ur"."scope_id" = "p_institution_id"
        ) THEN
            RAISE EXCEPTION 'Phase 8.1: active Faculty member in the institution required'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF NOT EXISTS (
            SELECT 1
              FROM "public"."sections" AS "section"
              JOIN "public"."course_offerings" AS "offering"
                ON "offering"."course_offering_id" = "section"."course_offering_id"
              JOIN "public"."courses" AS "course" ON "course"."course_id" = "offering"."course_id"
              JOIN "public"."departments" AS "department"
                ON "department"."department_id" = "course"."department_id"
             WHERE "section"."section_id" = "p_section_id"
               AND "section"."is_active" = true
               AND "offering"."is_active" = true
               AND "course"."is_active" = true
               AND "department"."is_active" = true
               AND "department"."institution_id" = "p_institution_id"
        ) THEN
            RAISE EXCEPTION 'Phase 8.1: active section in the institution required'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;

    IF "p_revoke" THEN
        UPDATE "public"."faculty_section_assignments"
           SET "revoked_by" = "p_actor_user_id", "revoked_at" = "now"()
         WHERE "faculty_user_id" = "p_faculty_user_id"
           AND "institution_id" = "p_institution_id"
           AND "section_id" = "p_section_id"
           AND "revoked_at" IS NULL
        RETURNING "faculty_section_assignments"."assignment_id" INTO "assignment_id";
        IF "assignment_id" IS NOT NULL THEN
            INSERT INTO "public"."admin_audit_log"
                ("actor_user_id", "institution_id", "action", "table_name",
                 "record_id", "record_data", "status")
            VALUES
                ("p_actor_user_id", "p_institution_id", 'faculty.assignment.revoke',
                 'faculty_section_assignments', "assignment_id"::text,
                 "jsonb_build_object"('faculty_user_id', "p_faculty_user_id",
                     'section_id', "p_section_id"), 'success');
        END IF;
        RETURN "assignment_id";
    END IF;

    INSERT INTO "public"."faculty_section_assignments"
        ("institution_id", "faculty_user_id", "section_id", "assigned_by")
    VALUES ("p_institution_id", "p_faculty_user_id", "p_section_id", "p_actor_user_id")
    ON CONFLICT ("faculty_user_id", "section_id") WHERE "revoked_at" IS NULL DO NOTHING
    RETURNING "faculty_section_assignments"."assignment_id" INTO "assignment_id";
    IF "assignment_id" IS NOT NULL THEN
        INSERT INTO "public"."admin_audit_log"
            ("actor_user_id", "institution_id", "action", "table_name",
             "record_id", "record_data", "status")
        VALUES
            ("p_actor_user_id", "p_institution_id", 'faculty.assignment.assign',
             'faculty_section_assignments', "assignment_id"::text,
             "jsonb_build_object"('faculty_user_id', "p_faculty_user_id",
                 'section_id', "p_section_id"), 'success');
    ELSE
        SELECT "assignment"."assignment_id" INTO "assignment_id"
          FROM "public"."faculty_section_assignments" AS "assignment"
         WHERE "assignment"."faculty_user_id" = "p_faculty_user_id"
           AND "assignment"."section_id" = "p_section_id"
           AND "assignment"."revoked_at" IS NULL;
    END IF;
    RETURN "assignment_id";
END;
$$;


ALTER FUNCTION "public"."phase81_manage_faculty_section_assignment_original"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase81_manage_staff_permission_grants"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_target_user_id" "uuid", "p_permission_codes" "text"[], "p_grant" boolean) RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    "permission_code" text;
    "permission_row" "public"."permissions"%ROWTYPE;
    "changed_count" integer := 0;
    "grant_id" uuid;
BEGIN
    PERFORM "public"."phase81_assert_institution_admin"(
        "p_actor_user_id", "p_institution_id"
    );
    IF "p_actor_user_id" = "p_target_user_id" THEN
        RAISE EXCEPTION 'Phase 8.1: administrators cannot grant Staff permissions to themselves'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."users" AS "target"
          JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "target"."id"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
         WHERE "target"."id" = "p_target_user_id"
           AND "target"."status" = 'active'
           AND "r"."name" = 'staff'
           AND "r"."is_active" = true
           AND "ur"."scope_type" = 'institution'
           AND "ur"."scope_id" = "p_institution_id"
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active Staff member in the institution required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF COALESCE("array_length"("p_permission_codes", 1), 0) = 0
       OR "array_length"("p_permission_codes", 1) > 32 THEN
        RAISE EXCEPTION 'Phase 8.1: permission list must contain 1 to 32 entries'
            USING ERRCODE = 'check_violation';
    END IF;
    IF "array_length"("p_permission_codes", 1) <>
       (SELECT "count"(DISTINCT "code") FROM "unnest"("p_permission_codes") AS "codes"("code")) THEN
        RAISE EXCEPTION 'Phase 8.1: duplicate permission codes are not accepted'
            USING ERRCODE = 'check_violation';
    END IF;

    FOREACH "permission_code" IN ARRAY "p_permission_codes"
    LOOP
        IF "permission_code" <> ALL (ARRAY[
            'ai.knowledge.create', 'attendance.read', 'attendance.manage',
            'results.read', 'results.manage', 'students.read', 'students.update',
            'documents.read', 'documents.create', 'documents.update',
            'notices.read', 'notices.create', 'notices.update'
        ]::text[]) THEN
            RAISE EXCEPTION 'Phase 8.1: permission is outside the Staff delegation allowlist'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        SELECT * INTO "permission_row"
          FROM "public"."permissions"
         WHERE "code" = "permission_code";
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Phase 8.1: unknown or inactive permission'
                USING ERRCODE = 'check_violation';
        END IF;
        IF "p_grant" AND NOT "permission_row"."is_active" THEN
            RAISE EXCEPTION 'Phase 8.1: unknown or inactive permission'
                USING ERRCODE = 'check_violation';
        END IF;

        IF "p_grant" THEN
            INSERT INTO "public"."user_permission_grants"
                ("user_id", "institution_id", "permission_id", "granted_by")
            VALUES
                ("p_target_user_id", "p_institution_id", "permission_row"."permission_id", "p_actor_user_id")
            ON CONFLICT ("user_id", "institution_id", "permission_id")
                WHERE "revoked_at" IS NULL DO NOTHING
            RETURNING "user_permission_grants"."grant_id" INTO "grant_id";
            IF "grant_id" IS NOT NULL THEN
                INSERT INTO "public"."admin_audit_log"
                    ("actor_user_id", "institution_id", "action", "table_name",
                     "record_id", "record_data", "status")
                VALUES
                    ("p_actor_user_id", "p_institution_id", 'permission.grant',
                     'user_permission_grants', "grant_id"::text,
                     "jsonb_build_object"('target_user_id', "p_target_user_id",
                         'permission_code', "permission_code", 'source', 'direct'),
                     'success');
                "changed_count" := "changed_count" + 1;
            END IF;
            "grant_id" := NULL;
        ELSE
            UPDATE "public"."user_permission_grants"
               SET "revoked_by" = "p_actor_user_id", "revoked_at" = "now"()
             WHERE "user_id" = "p_target_user_id"
               AND "institution_id" = "p_institution_id"
               AND "permission_id" = "permission_row"."permission_id"
               AND "revoked_at" IS NULL
            RETURNING "grant_id" INTO "grant_id";
            IF "grant_id" IS NOT NULL THEN
                INSERT INTO "public"."admin_audit_log"
                    ("actor_user_id", "institution_id", "action", "table_name",
                     "record_id", "record_data", "status")
                VALUES
                    ("p_actor_user_id", "p_institution_id", 'permission.revoke',
                     'user_permission_grants', "grant_id"::text,
                     "jsonb_build_object"('target_user_id', "p_target_user_id",
                         'permission_code', "permission_code", 'source', 'direct'),
                     'success');
                "changed_count" := "changed_count" + 1;
            END IF;
            "grant_id" := NULL;
        END IF;
    END LOOP;
    RETURN "changed_count";
END;
$$;


ALTER FUNCTION "public"."phase81_manage_staff_permission_grants"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_target_user_id" "uuid", "p_permission_codes" "text"[], "p_grant" boolean) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."phase81_prevent_audit_mutation"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
    RAISE EXCEPTION 'Audit records are append-only'
        USING ERRCODE = 'insufficient_privilege';
END;
$$;


ALTER FUNCTION "public"."phase81_prevent_audit_mutation"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reconcile_faculty_attendance_roster_student"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE r public.faculty_attendance_rosters; identity jsonb; student uuid;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || NEW.institution_id::text, 0));
    FOR r IN SELECT * FROM faculty_attendance_rosters WHERE institution_id = NEW.institution_id
        AND (linked_student_id = NEW.student_id OR register_number = NEW.register_number OR
             (NEW.university_roll_number IS NOT NULL AND university_roll_number = NEW.university_roll_number)) FOR UPDATE LOOP
        identity := faculty_attendance_identity(NEW.institution_id, r.register_number, r.university_roll_number);
        student := (identity->>'student_id')::uuid;
        IF (identity->>'conflict')::boolean OR (r.linked_student_id IS NOT NULL AND r.linked_student_id IS DISTINCT FROM student) THEN
            UPDATE faculty_attendance_rosters SET reconciliation_state = 'CONFLICT',
                reconciliation_errors = '["Conflicting or ambiguous student identifiers require administrator reconciliation"]'::jsonb
              WHERE roster_id = r.roster_id;
        ELSIF student = NEW.student_id THEN
            IF NEW.approval_status = 'approved' THEN
                UPDATE faculty_attendance_rosters SET linked_student_id = student, reconciliation_state = 'LINKED', reconciliation_errors = '[]',
                    roster_status = CASE WHEN NEW.is_active AND NEW.status = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END WHERE roster_id = r.roster_id;
                INSERT INTO student_attendance(student_id, institution_id, section_id, academic_year_id, semester_id, date, status, notes)
                SELECT student, NEW.institution_id, s.section_id, co.academic_year_id, co.semester_id, s.session_date, rec.status, rec.notes
                FROM faculty_attendance_records rec JOIN faculty_attendance_sessions s ON s.session_id = rec.session_id
                JOIN course_offerings co ON co.course_offering_id = s.course_offering_id WHERE rec.roster_id = r.roster_id
                ON CONFLICT(student_id, section_id, date) DO NOTHING;
            ELSE
                UPDATE faculty_attendance_rosters SET reconciliation_state = 'PENDING', roster_status = 'PENDING_APPROVAL'
                  WHERE roster_id = r.roster_id AND linked_student_id IS NULL;
            END IF;
        END IF;
        INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
        VALUES(NEW.user_id, NEW.institution_id, 'attendance.identity.reconcile', 'faculty_attendance_rosters', r.roster_id::text,
            jsonb_build_object('conflict', (identity->>'conflict')::boolean, 'approval_status', NEW.approval_status), 'success');
    END LOOP;
    RETURN NEW;
END; $$;


ALTER FUNCTION "public"."reconcile_faculty_attendance_roster_student"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reconcile_faculty_test_roster"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE previous_setting text:=current_setting('collegeai.test_write',true);
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||NEW.institution_id::text,0));
 PERFORM set_config('collegeai.test_write','reconcile',true);
 UPDATE test_results SET student_id=NEW.linked_student_id WHERE roster_id=NEW.roster_id AND test_id IS NOT NULL;
 PERFORM set_config('collegeai.test_write',coalesce(previous_setting,''),true);
 RETURN NEW;
END; $$;


ALTER FUNCTION "public"."reconcile_faculty_test_roster"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."refresh_student_test_visibility"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE previous_setting text:=current_setting('collegeai.test_write',true);
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||NEW.institution_id::text,0));
 PERFORM set_config('collegeai.test_write','reconcile',true);
 UPDATE test_results SET student_id=student_id WHERE student_id=NEW.student_id AND test_id IS NOT NULL;
 PERFORM set_config('collegeai.test_write',coalesce(previous_setting,''),true);
 RETURN NEW;
END; $$;


ALTER FUNCTION "public"."refresh_student_test_visibility"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."review_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_summary" "jsonb", "p_rows" "jsonb", "p_expected_updated_at" timestamp with time zone) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE item public.faculty_attendance_imports; row jsonb;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('attendance:' || p_tenant::text, 0));
    SELECT * INTO item FROM faculty_attendance_imports WHERE import_id = p_import_id AND institution_id = p_tenant FOR UPDATE;
    IF item.import_id IS NULL OR item.uploaded_by <> p_actor THEN RAISE EXCEPTION 'Import scope denied' USING ERRCODE = '42501'; END IF;
    PERFORM assert_faculty_attendance_mutation(p_actor, p_tenant, item.section_id);
    IF item.updated_at IS DISTINCT FROM p_expected_updated_at OR item.status = 'IMPORTED' THEN
        RAISE EXCEPTION 'Import changed' USING ERRCODE = '40001';
    END IF;
    DELETE FROM faculty_attendance_import_rows WHERE import_id = p_import_id;
    FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        INSERT INTO faculty_attendance_import_rows(import_id, row_number, raw_data, normalized_data, validation_status, errors, warnings)
        VALUES(p_import_id, (row->>'row_number')::integer, row->'raw_data', row->'normalized_data',
            row->>'validation_status', row->'errors', coalesce(row->'warnings','[]'::jsonb));
    END LOOP;
    UPDATE faculty_attendance_imports SET summary = p_summary, status = 'REVIEWED' WHERE import_id = p_import_id;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.review', 'faculty_attendance_imports', p_import_id::text, p_summary, 'success');
    RETURN jsonb_build_object('import_id', p_import_id);
END; $$;


ALTER FUNCTION "public"."review_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_summary" "jsonb", "p_rows" "jsonb", "p_expected_updated_at" timestamp with time zone) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."review_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_summary" "jsonb", "p_rows" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE i public.faculty_attendance_imports; t public.faculty_tests; row jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||p_tenant::text,0));
 SELECT * INTO i FROM faculty_attendance_imports WHERE import_id=p_import AND institution_id=p_tenant AND test_id IS NOT NULL FOR UPDATE;
 IF i.import_id IS NULL THEN RAISE EXCEPTION 'Import not found' USING ERRCODE='P0002'; END IF;
 SELECT version INTO t.version FROM faculty_tests WHERE test_id=i.test_id;
 t:=assert_test_version(p_actor,p_tenant,i.test_id,t.version);
 IF i.uploaded_by<>p_actor THEN RAISE EXCEPTION 'Import owner denied' USING ERRCODE='42501'; END IF;
 IF i.status='IMPORTED' OR i.updated_at IS DISTINCT FROM p_updated_at THEN RAISE EXCEPTION 'Import changed' USING ERRCODE='40001'; END IF;
 IF t.status<>'COMPLETED' OR t.marks_state<>'DRAFT' OR jsonb_array_length(p_rows) NOT BETWEEN 1 AND 500 THEN
   RAISE EXCEPTION 'Import not editable' USING ERRCODE='23514'; END IF;
 DELETE FROM faculty_attendance_import_rows WHERE import_id=p_import;
 FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
   INSERT INTO faculty_attendance_import_rows(import_id,row_number,raw_data,normalized_data,validation_status,errors,warnings)
   VALUES(p_import,(row->>'row_number')::int,row->'raw_data',row->'normalized_data',row->>'validation_status',row->'errors',row->'warnings');
 END LOOP;
 UPDATE faculty_attendance_imports SET status='REVIEWED',summary=p_summary WHERE import_id=p_import;
 INSERT INTO admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
 VALUES(p_actor,p_tenant,'test.import.review','faculty_tests',i.test_id::text,jsonb_build_object('import_id',p_import,'summary',p_summary),'success');
 RETURN jsonb_build_object('import_id',p_import);
END; $$;


ALTER FUNCTION "public"."review_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_summary" "jsonb", "p_rows" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."save_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_data" "jsonb", "p_test" "uuid" DEFAULT NULL::"uuid", "p_version" bigint DEFAULT NULL::bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE t public.faculty_tests; prior jsonb;
BEGIN
 PERFORM assert_faculty_academic_mutation(p_actor,p_tenant,p_section,'results.manage');
 PERFORM set_config('collegeai.test_write','rpc',true);
 IF p_test IS NOT NULL THEN
   t:=assert_test_version(p_actor,p_tenant,p_test,p_version); prior:=to_jsonb(t);
   IF t.section_id<>p_section OR t.status NOT IN ('DRAFT','SCHEDULED') OR EXISTS(SELECT 1 FROM test_results WHERE test_id=p_test) THEN
     RAISE EXCEPTION 'Assessment metadata is no longer editable' USING ERRCODE='23514';
   END IF;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM test_types WHERE code=p_data->>'test_type' AND is_active) THEN
   RAISE EXCEPTION 'Unknown assessment type' USING ERRCODE='23514';
 END IF;
 PERFORM validate_test_schedule(p_tenant,p_section,p_test,(p_data->>'scheduled_date')::date,
   (p_data->>'start_time')::time,(p_data->>'end_time')::time);
 IF p_test IS NULL THEN
   INSERT INTO faculty_tests(institution_id,section_id,title,test_type,description,max_marks,passing_marks,
     scheduled_date,start_time,end_time,duration_minutes,created_by,updated_by)
   VALUES(p_tenant,p_section,p_data->>'title',p_data->>'test_type',p_data->>'description',(p_data->>'max_marks')::numeric,
     (p_data->>'passing_marks')::numeric,(p_data->>'scheduled_date')::date,(p_data->>'start_time')::time,
     (p_data->>'end_time')::time,(p_data->>'duration_minutes')::int,p_actor,p_actor) RETURNING * INTO t;
 ELSE
   UPDATE faculty_tests SET title=p_data->>'title',test_type=p_data->>'test_type',description=p_data->>'description',
     max_marks=(p_data->>'max_marks')::numeric,passing_marks=(p_data->>'passing_marks')::numeric,
     scheduled_date=(p_data->>'scheduled_date')::date,start_time=(p_data->>'start_time')::time,end_time=(p_data->>'end_time')::time,
     duration_minutes=(p_data->>'duration_minutes')::int,version=version+1,updated_by=p_actor,updated_at=clock_timestamp()
   WHERE test_id=p_test RETURNING * INTO t;
 END IF;
 INSERT INTO admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
 VALUES(p_actor,p_tenant,CASE WHEN p_test IS NULL THEN 'test.create' ELSE 'test.update' END,'faculty_tests',t.test_id::text,
   jsonb_build_object('before',prior,'after',to_jsonb(t)),'success');
 RETURN to_jsonb(t);
END; $$;


ALTER FUNCTION "public"."save_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_data" "jsonb", "p_test" "uuid", "p_version" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."save_faculty_test_marks"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_rows" "jsonb", "p_reason" "text" DEFAULT NULL::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE t public.faculty_tests; r public.faculty_attendance_rosters; row jsonb; score numeric; old jsonb; identity jsonb; ctx jsonb; count_rows int:=0;
BEGIN
 t:=assert_test_version(p_actor,p_tenant,p_test,p_version);
 SELECT to_jsonb(co) INTO ctx FROM sections s JOIN course_offerings co USING(course_offering_id) WHERE s.section_id=t.section_id;
 IF (p_reason IS NULL AND (t.status<>'COMPLETED' OR t.marks_state<>'DRAFT')) OR
    (p_reason IS NOT NULL AND (t.status<>'LOCKED' OR length(btrim(p_reason)) NOT BETWEEN 10 AND 1000)) THEN
   RAISE EXCEPTION 'Marks cannot be edited in this state' USING ERRCODE='23514';
 END IF;
 IF jsonb_typeof(p_rows)<>'array' OR jsonb_array_length(p_rows) NOT BETWEEN 1 AND 500 OR
   (SELECT count(DISTINCT x->>'roster_id') FROM jsonb_array_elements(p_rows) x)<>jsonb_array_length(p_rows) THEN
   RAISE EXCEPTION 'Invalid or duplicate batch' USING ERRCODE='23514';
 END IF;
 FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
   SELECT * INTO r FROM faculty_attendance_rosters WHERE roster_id=(row->>'roster_id')::uuid
     AND institution_id=p_tenant AND section_id=t.section_id FOR SHARE;
   IF r.roster_id IS NULL OR r.reconciliation_state='CONFLICT' OR (r.roster_status='INACTIVE' AND p_reason IS NULL) THEN
     RAISE EXCEPTION 'Roster identity denied' USING ERRCODE='42501';
   END IF;
   identity:=faculty_attendance_identity(p_tenant,r.register_number,r.university_roll_number);
   IF (identity->>'conflict')::boolean OR
      (identity->>'program_id' IS NOT NULL AND identity->>'program_id'<>ctx->>'program_id') OR
      (identity->>'academic_year_id' IS NOT NULL AND identity->>'academic_year_id'<>ctx->>'academic_year_id') OR
      (r.linked_student_id IS NOT NULL AND r.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid) THEN
     RAISE EXCEPTION 'Roster identity conflicts with academic context' USING ERRCODE='42501'; END IF;
   IF row->>'mark_status' IS NULL OR row->>'mark_status' NOT IN ('present','absent','exempt','not_attempted','missing') THEN
     RAISE EXCEPTION 'Invalid mark status' USING ERRCODE='23514';
   END IF;
   score:=(row->>'scored_marks')::numeric;
   IF score<0 OR score>t.max_marks OR score<>round(score,2) OR
     ((row->>'mark_status'='present') IS DISTINCT FROM (score IS NOT NULL)) OR length(row->>'remarks')>1000 THEN
     RAISE EXCEPTION 'Invalid marks or precision' USING ERRCODE='23514';
   END IF;
   SELECT to_jsonb(m) INTO old FROM test_results m WHERE test_id=p_test AND roster_id=r.roster_id;
   IF p_reason IS NOT NULL AND old IS NULL THEN RAISE EXCEPTION 'Correction must replace an existing result' USING ERRCODE='23514'; END IF;
   INSERT INTO test_results(test_id,roster_id,student_id,institution_id,course_id,section_id,academic_year_id,semester_id,
     test_name,test_type,max_marks,scored_marks,percentage,conducted_at,status,mark_status,remarks)
   SELECT p_test,r.roster_id,r.linked_student_id,p_tenant,co.course_id,t.section_id,co.academic_year_id,co.semester_id,
     t.title,t.test_type,t.max_marks,score,round(score/t.max_marks*100,2),t.scheduled_date::timestamp,
     CASE WHEN t.status='LOCKED' THEN 'published' ELSE 'draft' END,row->>'mark_status',row->>'remarks'
   FROM sections s JOIN course_offerings co USING(course_offering_id) WHERE s.section_id=t.section_id
   ON CONFLICT(test_id,roster_id) WHERE test_id IS NOT NULL DO UPDATE SET
     scored_marks=EXCLUDED.scored_marks,percentage=EXCLUDED.percentage,mark_status=EXCLUDED.mark_status,remarks=EXCLUDED.remarks;
   INSERT INTO admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
   VALUES(p_actor,p_tenant,CASE WHEN p_reason IS NOT NULL THEN 'test.marks.post_lock_correct'
     WHEN old IS NULL THEN 'test.marks.enter' ELSE 'test.marks.correct' END,'faculty_tests',p_test::text,
     jsonb_build_object('roster_id',r.roster_id,'before',CASE WHEN old IS NOT NULL THEN
       jsonb_build_object('marks',old->'scored_marks','status',old->'mark_status','remarks',old->'remarks') ELSE NULL END,
       'after',jsonb_build_object('marks',score,'status',row->>'mark_status','remarks',row->>'remarks'),'reason',p_reason),'success');
   count_rows:=count_rows+1;
 END LOOP;
 UPDATE faculty_tests SET version=version+1,updated_by=p_actor,updated_at=clock_timestamp() WHERE test_id=p_test RETURNING * INTO t;
 RETURN jsonb_build_object('test_id',p_test,'version',t.version,'saved',count_rows);
END; $$;


ALTER FUNCTION "public"."save_faculty_test_marks"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_rows" "jsonb", "p_reason" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."search_public_knowledge_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid" DEFAULT NULL::"uuid", "filter_model_name" "text" DEFAULT NULL::"text") RETURNS TABLE("chunk_id" "uuid", "document_id" "uuid", "document_version_id" "uuid", "content_text" "text", "processing_run_id" "uuid", "chunk_sequence" integer, "section_title" "text", "source_title" "text", "source_type" "text", "model_name" "text", "distance" double precision)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public', 'extensions'
    AS $$
    SELECT
        kc.chunk_id,
        d.document_id,
        dv.document_version_id,
        kc.content_text,
        dpr.processing_run_id,
        kc.chunk_sequence,
        kc.section_title,
        ks.title AS source_title,
        ks.source_type,
        ce.model_name,
        ce.embedding <=> query_embedding AS distance
    FROM public.chunk_embeddings AS ce
    JOIN public.knowledge_chunks AS kc
      ON kc.chunk_id = ce.chunk_id
    JOIN public.document_processing_runs AS dpr
      ON dpr.processing_run_id = kc.processing_run_id
    JOIN public.document_versions AS dv
      ON dv.document_version_id = dpr.document_version_id
    JOIN public.documents AS d
      ON d.document_id = dv.document_id
    JOIN public.knowledge_sources AS ks
      ON ks.knowledge_source_id = d.knowledge_source_id
    WHERE match_count BETWEEN 1 AND 20
      AND filter_institution_id IS NOT NULL
      AND ks.institution_id = filter_institution_id
      AND ks.visibility = 'public'
      AND ks.lifecycle_status = 'published'
      AND (ks.effective_from IS NULL OR ks.effective_from <= CURRENT_DATE)
      AND (ks.effective_until IS NULL OR ks.effective_until >= CURRENT_DATE)
      AND dv.lifecycle_status = 'published'
      AND (dv.effective_from IS NULL OR dv.effective_from <= CURRENT_DATE)
      AND (dv.effective_until IS NULL OR dv.effective_until >= CURRENT_DATE)
      AND dpr.status = 'ready'
      AND dpr.embedding_status = 'embedded'
      AND dpr.completed_at IS NOT NULL
      AND ce.embedding_dimensions = 1536
      AND (filter_knowledge_source_id IS NULL OR ks.knowledge_source_id = filter_knowledge_source_id)
      AND (filter_model_name IS NULL OR ce.model_name = filter_model_name)
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT LEAST(match_count, 20);
$$;


ALTER FUNCTION "public"."search_public_knowledge_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid", "filter_model_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."search_similar_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid" DEFAULT NULL::"uuid", "filter_knowledge_source_id" "uuid" DEFAULT NULL::"uuid", "filter_document_id" "uuid" DEFAULT NULL::"uuid", "filter_document_version_id" "uuid" DEFAULT NULL::"uuid", "filter_processing_run_id" "uuid" DEFAULT NULL::"uuid", "filter_model_name" "text" DEFAULT NULL::"text") RETURNS TABLE("chunk_id" "uuid", "document_id" "uuid", "document_version_id" "uuid", "content_text" "text", "processing_run_id" "uuid", "chunk_sequence" integer, "section_title" "text", "model_name" "text", "distance" double precision)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public', 'extensions'
    AS $$
    SELECT
        kc.chunk_id,
        dv.document_id,
        dv.document_version_id,
        kc.content_text,
        kc.processing_run_id,
        kc.chunk_sequence,
        kc.section_title,
        ce.model_name,
        ce.embedding <=> query_embedding AS distance
    FROM public.chunk_embeddings AS ce
    JOIN public.knowledge_chunks AS kc
        ON kc.chunk_id = ce.chunk_id
    JOIN public.document_processing_runs AS dpr
        ON dpr.processing_run_id = kc.processing_run_id
    JOIN public.document_versions AS dv
        ON dv.document_version_id = dpr.document_version_id
    JOIN public.documents AS d
        ON d.document_id = dv.document_id
    JOIN public.knowledge_sources AS ks
        ON ks.knowledge_source_id = d.knowledge_source_id
    WHERE (filter_institution_id IS NULL OR ks.institution_id = filter_institution_id)
      AND (filter_knowledge_source_id IS NULL OR ks.knowledge_source_id = filter_knowledge_source_id)
      AND (filter_document_id IS NULL OR d.document_id = filter_document_id)
      AND (filter_document_version_id IS NULL OR dv.document_version_id = filter_document_version_id)
      AND (filter_processing_run_id IS NULL OR kc.processing_run_id = filter_processing_run_id)
      AND (filter_model_name IS NULL OR ce.model_name = filter_model_name)
      AND (
          filter_institution_id IS NOT NULL
          OR filter_knowledge_source_id IS NOT NULL
          OR filter_document_id IS NOT NULL
          OR filter_document_version_id IS NOT NULL
          OR filter_processing_run_id IS NOT NULL
          OR filter_model_name IS NOT NULL
      )
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT match_count;
$$;


ALTER FUNCTION "public"."search_similar_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid", "filter_document_id" "uuid", "filter_document_version_id" "uuid", "filter_processing_run_id" "uuid", "filter_model_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."stage_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_semester_id" "uuid", "p_filename" "text", "p_file_type" "text", "p_strategy" "text", "p_ai_confirmed" boolean, "p_summary" "jsonb", "p_rows" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE ctx jsonb; id uuid; row jsonb;
BEGIN
    ctx := assert_faculty_attendance_mutation(p_actor, p_tenant, p_section_id);
    IF ctx->>'semester_id' <> p_semester_id::text THEN
        RAISE EXCEPTION 'Semester scope mismatch' USING ERRCODE = '23514';
    END IF;
    INSERT INTO faculty_attendance_imports(institution_id, section_id, course_offering_id, academic_year_id,
        semester_id, uploaded_by, original_filename, file_type, processing_strategy,
        ai_confirmation_required, ai_confirmed_at, status, summary)
    VALUES(p_tenant, p_section_id, (ctx->>'course_offering_id')::uuid, (ctx->>'academic_year_id')::uuid,
        p_semester_id, p_actor, p_filename, p_file_type, p_strategy, p_strategy = 'OCR_AI',
        CASE WHEN p_ai_confirmed THEN now() ELSE NULL END, 'VALIDATED', p_summary) RETURNING import_id INTO id;
    FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
        INSERT INTO faculty_attendance_import_rows(import_id, row_number, raw_data, normalized_data, validation_status, errors, warnings)
        VALUES(id, (row->>'row_number')::integer, row->'raw_data', row->'normalized_data', row->>'validation_status', row->'errors', coalesce(row->'warnings','[]'::jsonb));
    END LOOP;
    INSERT INTO admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor, p_tenant, 'attendance.import.create', 'faculty_attendance_imports', id::text, p_summary, 'success');
    RETURN jsonb_build_object('import_id', id);
END; $$;


ALTER FUNCTION "public"."stage_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_semester_id" "uuid", "p_filename" "text", "p_file_type" "text", "p_strategy" "text", "p_ai_confirmed" boolean, "p_summary" "jsonb", "p_rows" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."stage_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_filename" "text", "p_strategy" "text", "p_summary" "jsonb", "p_rows" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE t public.faculty_tests; item uuid; row jsonb;
BEGIN
 SELECT version INTO t.version FROM faculty_tests WHERE test_id=p_test AND institution_id=p_tenant;
 t:=assert_test_version(p_actor,p_tenant,p_test,t.version);
 IF t.status<>'COMPLETED' OR t.marks_state<>'DRAFT' OR p_strategy NOT IN ('CSV','XLS','XLSX') OR
   jsonb_typeof(p_rows)<>'array' OR jsonb_array_length(p_rows) NOT BETWEEN 1 AND 500 THEN
   RAISE EXCEPTION 'Import is unavailable in this state' USING ERRCODE='23514'; END IF;
 INSERT INTO faculty_attendance_imports(institution_id,section_id,course_offering_id,academic_year_id,semester_id,
   uploaded_by,original_filename,file_type,processing_strategy,status,summary,test_id)
 SELECT p_tenant,t.section_id,co.course_offering_id,co.academic_year_id,co.semester_id,p_actor,p_filename,lower(p_strategy),p_strategy,'VALIDATED',p_summary,p_test
 FROM sections s JOIN course_offerings co USING(course_offering_id) WHERE s.section_id=t.section_id RETURNING import_id INTO item;
 FOR row IN SELECT * FROM jsonb_array_elements(p_rows) LOOP
   INSERT INTO faculty_attendance_import_rows(import_id,row_number,raw_data,normalized_data,validation_status,errors,warnings)
   VALUES(item,(row->>'row_number')::int,row->'raw_data',row->'normalized_data',row->>'validation_status',row->'errors',row->'warnings');
 END LOOP;
 INSERT INTO admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
 VALUES(p_actor,p_tenant,'test.import.create','faculty_tests',p_test::text,jsonb_build_object('import_id',item,'summary',p_summary),'success');
 RETURN jsonb_build_object('import_id',item);
END; $$;


ALTER FUNCTION "public"."stage_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_filename" "text", "p_strategy" "text", "p_summary" "jsonb", "p_rows" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."student_attendance_tenant_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."student_attendance_tenant_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."student_results_tenant_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_student_institution_id "uuid";
    v_ay_institution_id "uuid";
    v_semester_academic_year_id "uuid";
    v_program_institution_id "uuid";
BEGIN
    SELECT "s"."institution_id" INTO v_student_institution_id
    FROM "public"."students" AS "s"
    WHERE "s"."student_id" = NEW."student_id";

    IF v_student_institution_id IS NULL THEN
        RAISE EXCEPTION 'result student does not exist';
    END IF;

    -- The tenant is server-derived from the student record; any
    -- caller-supplied value is overridden.
    NEW."institution_id" := v_student_institution_id;

    SELECT "ay"."institution_id" INTO v_ay_institution_id
    FROM "public"."academic_years" AS "ay"
    WHERE "ay"."academic_year_id" = NEW."academic_year_id";

    IF v_ay_institution_id IS NULL THEN
        RAISE EXCEPTION 'result academic year does not exist';
    END IF;

    IF v_ay_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'result student and academic year belong to different institutions';
    END IF;

    SELECT "sem"."academic_year_id" INTO v_semester_academic_year_id
    FROM "public"."semesters" AS "sem"
    WHERE "sem"."semester_id" = NEW."semester_id";

    IF v_semester_academic_year_id IS NULL THEN
        RAISE EXCEPTION 'result semester does not exist';
    END IF;

    IF v_semester_academic_year_id IS DISTINCT FROM NEW."academic_year_id" THEN
        RAISE EXCEPTION 'result semester must belong to the result academic year';
    END IF;

    SELECT "d"."institution_id" INTO v_program_institution_id
    FROM "public"."programs" AS "p"
    JOIN "public"."departments" AS "d"
        ON "d"."department_id" = "p"."department_id"
    WHERE "p"."program_id" = NEW."program_id";

    IF v_program_institution_id IS NULL THEN
        RAISE EXCEPTION 'result program academic chain cannot be resolved';
    END IF;

    IF v_program_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'result student and program belong to different institutions';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF NEW."student_id"      IS DISTINCT FROM OLD."student_id"
           OR NEW."academic_year_id" IS DISTINCT FROM OLD."academic_year_id"
           OR NEW."semester_id"  IS DISTINCT FROM OLD."semester_id"
           OR NEW."program_id"   IS DISTINCT FROM OLD."program_id" THEN
            RAISE EXCEPTION 'result ownership fields cannot be changed';
        END IF;
        NEW."updated_at" := "now"();
    END IF;

    RETURN "NEW";
END;
$$;


ALTER FUNCTION "public"."student_results_tenant_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."test_results_tenant_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    t public.faculty_tests; r public.faculty_attendance_rosters; co public.course_offerings;
    v_student_institution_id "uuid";
    v_ay_institution_id "uuid";
    v_course_institution_id "uuid";
    v_section_course_id "uuid";
    v_section_academic_year_id "uuid";
    v_section_semester_id "uuid";
    v_section_institution_id "uuid";
BEGIN

    IF NEW.test_id IS NOT NULL THEN
        IF current_setting('collegeai.test_write',true) NOT IN ('rpc','reconcile') OR current_setting('collegeai.test_write',true) IS NULL THEN
            RAISE EXCEPTION 'Workflow results require the authorized transaction' USING ERRCODE='42501';
        END IF;
        SELECT * INTO t FROM faculty_tests WHERE test_id=NEW.test_id;
        SELECT * INTO r FROM faculty_attendance_rosters WHERE roster_id=NEW.roster_id;
        SELECT o.* INTO co FROM sections s JOIN course_offerings o USING(course_offering_id) WHERE s.section_id=t.section_id;
        IF r.section_id IS DISTINCT FROM t.section_id OR r.institution_id IS DISTINCT FROM t.institution_id THEN
            RAISE EXCEPTION 'Result roster scope mismatch' USING ERRCODE='23514';
        END IF;
        IF TG_OP='UPDATE' AND (NEW.test_id IS DISTINCT FROM OLD.test_id OR NEW.roster_id IS DISTINCT FROM OLD.roster_id) THEN
            RAISE EXCEPTION 'Result identity is immutable' USING ERRCODE='23514'; END IF;
        IF current_setting('collegeai.test_write',true)='reconcile' AND TG_OP='UPDATE' AND
            (NEW.scored_marks IS DISTINCT FROM OLD.scored_marks OR NEW.mark_status IS DISTINCT FROM OLD.mark_status OR NEW.remarks IS DISTINCT FROM OLD.remarks) THEN
            RAISE EXCEPTION 'Reconciliation cannot modify marks' USING ERRCODE='42501'; END IF;
        NEW.student_id:=r.linked_student_id;
        NEW.institution_id:=t.institution_id; NEW.section_id:=t.section_id; NEW.course_id:=co.course_id;
        NEW.academic_year_id:=co.academic_year_id; NEW.semester_id:=co.semester_id;
        NEW.test_name:=t.title; NEW.test_type:=t.test_type; NEW.max_marks:=t.max_marks;
        NEW.percentage:=round(NEW.scored_marks/t.max_marks*100,2); NEW.conducted_at:=t.scheduled_date::timestamp;
        NEW.status:=CASE WHEN t.status IN ('PUBLISHED','LOCKED') AND r.reconciliation_state<>'CONFLICT'
            AND r.roster_status='ACTIVE' AND EXISTS(SELECT 1 FROM students s WHERE s.student_id=r.linked_student_id
              AND s.institution_id=t.institution_id AND s.approval_status='approved' AND s.is_active AND s.status='active'
              AND (s.program_id IS NULL OR s.program_id=co.program_id)
              AND (s.academic_year_id IS NULL OR s.academic_year_id=co.academic_year_id)) THEN 'published' ELSE 'draft' END;
        NEW.updated_at:=clock_timestamp(); RETURN NEW;
    END IF;
    IF TG_OP='UPDATE' AND OLD.test_id IS NOT NULL THEN
        RAISE EXCEPTION 'Workflow result cannot become a legacy result' USING ERRCODE='42501'; END IF;
    SELECT "s"."institution_id" INTO v_student_institution_id
    FROM "public"."students" AS "s"
    WHERE "s"."student_id" = NEW."student_id";

    IF v_student_institution_id IS NULL THEN
        RAISE EXCEPTION 'test result student does not exist';
    END IF;

    -- The tenant is server-derived from the student record; any
    -- caller-supplied value is overridden.
    NEW."institution_id" := v_student_institution_id;

    SELECT "ay"."institution_id" INTO v_ay_institution_id
    FROM "public"."academic_years" AS "ay"
    WHERE "ay"."academic_year_id" = NEW."academic_year_id";

    IF v_ay_institution_id IS NULL THEN
        RAISE EXCEPTION 'test result academic year does not exist';
    END IF;

    IF v_ay_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'test result student and academic year belong to different institutions';
    END IF;

    SELECT "d"."institution_id" INTO v_course_institution_id
    FROM "public"."courses" AS "c"
    JOIN "public"."departments" AS "d"
        ON "d"."department_id" = "c"."department_id"
    WHERE "c"."course_id" = NEW."course_id";

    IF v_course_institution_id IS NULL THEN
        RAISE EXCEPTION 'test result course academic chain cannot be resolved';
    END IF;

    IF v_course_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'test result student and course belong to different institutions';
    END IF;

    IF NEW."section_id" IS NOT NULL THEN
        SELECT "co"."course_id", "co"."academic_year_id", "co"."semester_id",
               "d"."institution_id"
        INTO v_section_course_id, v_section_academic_year_id,
             v_section_semester_id, v_section_institution_id
        FROM "public"."sections" AS "sec"
        JOIN "public"."course_offerings" AS "co"
            ON "co"."course_offering_id" = "sec"."course_offering_id"
        JOIN "public"."courses" AS "c"
            ON "c"."course_id" = "co"."course_id"
        JOIN "public"."departments" AS "d"
            ON "d"."department_id" = "c"."department_id"
        WHERE "sec"."section_id" = NEW."section_id";

        IF v_section_institution_id IS NULL THEN
            RAISE EXCEPTION 'test result section academic chain cannot be resolved';
        END IF;

        IF v_section_institution_id IS DISTINCT FROM v_student_institution_id THEN
            RAISE EXCEPTION 'test result student and section belong to different institutions';
        END IF;

        IF v_section_course_id IS DISTINCT FROM NEW."course_id"
           OR v_section_academic_year_id IS DISTINCT FROM NEW."academic_year_id"
           OR v_section_semester_id IS DISTINCT FROM NEW."semester_id" THEN
            RAISE EXCEPTION 'test result academic context must match the section offering';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF NEW."student_id"      IS DISTINCT FROM OLD."student_id"
           OR NEW."course_id"    IS DISTINCT FROM OLD."course_id"
           OR NEW."academic_year_id" IS DISTINCT FROM OLD."academic_year_id"
           OR NEW."semester_id"  IS DISTINCT FROM OLD."semester_id" THEN
            RAISE EXCEPTION 'test result ownership fields cannot be changed';
        END IF;
        NEW."updated_at" := "now"();
    END IF;

    RETURN "NEW";
END;
$$;


ALTER FUNCTION "public"."test_results_tenant_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."transition_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_action" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE t public.faculty_tests; previous jsonb; next_status text; checked_roster public.faculty_attendance_rosters; identity jsonb; co public.course_offerings;
BEGIN
 t:=assert_test_version(p_actor,p_tenant,p_test,p_version); previous:=jsonb_build_object('status',t.status,'marks_state',t.marks_state);
 next_status:=CASE
   WHEN p_action='schedule' AND t.status='DRAFT' THEN 'SCHEDULED'
   WHEN p_action='start' AND t.status='SCHEDULED' THEN 'ONGOING'
   WHEN p_action='complete' AND t.status IN ('SCHEDULED','ONGOING') THEN 'COMPLETED'
   WHEN p_action='publish' AND t.status='COMPLETED' AND t.marks_state='SUBMITTED' THEN 'PUBLISHED'
   WHEN p_action='lock' AND t.status='PUBLISHED' THEN 'LOCKED'
   WHEN p_action='cancel' AND t.status IN ('DRAFT','SCHEDULED','ONGOING','COMPLETED') THEN 'CANCELLED'
   WHEN p_action='submit' AND t.status='COMPLETED' AND t.marks_state='DRAFT' THEN t.status
   WHEN p_action='return_marks' AND t.status='COMPLETED' AND t.marks_state='SUBMITTED' THEN t.status ELSE NULL END;
 IF next_status IS NULL THEN RAISE EXCEPTION 'Invalid lifecycle transition' USING ERRCODE='23514'; END IF;
 IF p_action IN ('schedule','start','complete') THEN
   IF t.scheduled_date IS NULL THEN RAISE EXCEPTION 'Scheduled date is required' USING ERRCODE='23514'; END IF;
   PERFORM validate_test_schedule(p_tenant,t.section_id,p_test,t.scheduled_date,t.start_time,t.end_time);
 END IF;
 IF p_action IN ('submit','publish') THEN
   SELECT o.* INTO co FROM sections s JOIN course_offerings o USING(course_offering_id) WHERE s.section_id=t.section_id;
   FOR checked_roster IN SELECT * FROM faculty_attendance_rosters WHERE institution_id=p_tenant AND section_id=t.section_id AND roster_status<>'INACTIVE' FOR SHARE LOOP
     identity:=faculty_attendance_identity(p_tenant,checked_roster.register_number,checked_roster.university_roll_number);
     IF (identity->>'conflict')::boolean OR
       (identity->>'program_id' IS NOT NULL AND (identity->>'program_id')::uuid<>co.program_id) OR
       (identity->>'academic_year_id' IS NOT NULL AND (identity->>'academic_year_id')::uuid<>co.academic_year_id) OR
       (checked_roster.linked_student_id IS NOT NULL AND checked_roster.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid) THEN
       RAISE EXCEPTION 'Roster identity conflicts prevent submission/publication' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF NOT EXISTS(SELECT 1 FROM test_results WHERE test_id=p_test) OR EXISTS(
     SELECT 1 FROM faculty_attendance_rosters r LEFT JOIN test_results m ON m.roster_id=r.roster_id AND m.test_id=p_test
     WHERE r.section_id=t.section_id AND r.institution_id=p_tenant AND r.roster_status<>'INACTIVE'
       AND (r.reconciliation_state='CONFLICT' OR m.test_result_id IS NULL OR m.mark_status='missing')) THEN
     RAISE EXCEPTION 'Every active roster identity requires valid explicit marks or status' USING ERRCODE='23514';
   END IF;
 END IF;
 UPDATE faculty_tests SET status=next_status,
   marks_state=CASE WHEN p_action='submit' THEN 'SUBMITTED' WHEN p_action='return_marks' THEN 'DRAFT' ELSE marks_state END,
   version=version+1,updated_by=p_actor,updated_at=clock_timestamp() WHERE test_id=p_test RETURNING * INTO t;
 IF p_action='publish' THEN UPDATE test_results SET status='published' WHERE test_id=p_test; END IF;
 INSERT INTO admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
 VALUES(p_actor,p_tenant,'test.'||p_action,'faculty_tests',p_test::text,
   jsonb_build_object('before',previous,'after',jsonb_build_object('status',t.status,'marks_state',t.marks_state)),'success');
 RETURN to_jsonb(t);
END; $$;


ALTER FUNCTION "public"."transition_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_action" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."trg_student_notifications_tenant_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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
$$;


ALTER FUNCTION "public"."trg_student_notifications_tenant_guard"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_faculty_teaching_validity"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE before_row jsonb; after_row jsonb;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    IF NOT EXISTS (SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id JOIN public.permissions p ON p.permission_id = rp.permission_id
        WHERE ur.user_id = p_actor_user_id AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND r.name = 'admin' AND r.is_active AND p.code = 'faculty.assignments.manage' AND p.is_active)
    THEN RAISE EXCEPTION 'Assignment permission required' USING ERRCODE = '42501'; END IF;
    SELECT to_jsonb(f.*) INTO before_row FROM public.faculty_section_assignments f
        WHERE assignment_id = p_assignment_id AND institution_id = p_institution_id AND revoked_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Teaching assignment not found' USING ERRCODE = 'P0002'; END IF;
    IF (before_row->>'faculty_user_id')::uuid = p_actor_user_id THEN
        RAISE EXCEPTION 'Self-assignment denied' USING ERRCODE = '42501'; END IF;
    IF p_is_active AND NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id=u.id JOIN public.roles r ON r.id=ur.role_id
        WHERE u.id=(before_row->>'faculty_user_id')::uuid AND u.status='active' AND r.name='faculty' AND r.is_active
          AND ur.scope_type='institution' AND ur.scope_id=p_institution_id
    ) THEN RAISE EXCEPTION 'Active Faculty in the institution required' USING ERRCODE = '23514'; END IF;
    UPDATE public.faculty_section_assignments SET start_at = p_start_at, end_at = p_end_at, is_active = p_is_active
        WHERE assignment_id = p_assignment_id RETURNING to_jsonb(faculty_section_assignments.*) INTO after_row;
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
    VALUES(p_actor_user_id, p_institution_id, 'faculty.assignment.update', 'faculty_section_assignments',
        p_assignment_id::text, jsonb_build_object('before',before_row,'after',after_row), 'success');
    RETURN p_assignment_id;
END; $$;


ALTER FUNCTION "public"."update_faculty_teaching_validity"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."validate_academic_master_record"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE
    item jsonb := to_jsonb(NEW);
    previous jsonb;
    key text;
    owner uuid;
    parent_owner uuid;
    year_row public.academic_years;
    program_row public.programs;
    course_row public.courses;
    semester_row public.semesters;
    offering_row public.course_offerings;
    check_active boolean;
BEGIN
    IF TG_OP='UPDATE' THEN
        previous := to_jsonb(OLD);
        FOR key IN SELECT jsonb_object_keys(item) LOOP
            IF (key LIKE '%\_id' ESCAPE '\' OR (TG_TABLE_NAME='sections' AND key='code'))
               AND item->key IS DISTINCT FROM previous->key THEN
                RAISE EXCEPTION 'Academic ancestry is immutable' USING ERRCODE='22023';
            END IF;
        END LOOP;
    END IF;
    IF item ? 'name' AND btrim(item->>'name')='' OR item ? 'code' AND btrim(item->>'code')='' THEN
        RAISE EXCEPTION 'Academic name and code must be nonblank' USING ERRCODE='23514';
    END IF;
    check_active := TG_OP='INSERT' OR (NEW.is_active AND NOT OLD.is_active);
    CASE TG_TABLE_NAME
    WHEN 'departments', 'academic_years' THEN owner := (item->>'institution_id')::uuid;
    WHEN 'programs', 'courses' THEN owner := public.academic_master_tenant('departments', (item->>'department_id')::uuid);
    WHEN 'semesters' THEN owner := public.academic_master_tenant('academic_years', (item->>'academic_year_id')::uuid);
    WHEN 'program_courses', 'course_offerings' THEN owner := public.academic_master_tenant('programs', (item->>'program_id')::uuid);
    WHEN 'sections' THEN owner := public.academic_master_tenant('course_offerings', (item->>'course_offering_id')::uuid);
    END CASE;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:' || owner::text, 0));
    CASE TG_TABLE_NAME
    WHEN 'departments', 'academic_years' THEN
        owner := (item->>'institution_id')::uuid;
        IF check_active AND NOT EXISTS(SELECT 1 FROM public.institutions i WHERE i.institution_id=owner AND i.is_active AND i.status='active') THEN
            RAISE EXCEPTION 'Active institution required' USING ERRCODE='23514';
        END IF;
    WHEN 'programs', 'courses' THEN
        owner := public.academic_master_tenant('departments', (item->>'department_id')::uuid);
        IF check_active AND NOT EXISTS(SELECT 1 FROM public.departments d WHERE d.department_id=(item->>'department_id')::uuid AND d.is_active) THEN
            RAISE EXCEPTION 'Active department required' USING ERRCODE='23514';
        END IF;
    WHEN 'semesters' THEN
        SELECT * INTO year_row FROM public.academic_years y WHERE y.academic_year_id=(item->>'academic_year_id')::uuid;
        owner := year_row.institution_id;
        IF (item->>'start_date')::date < year_row.start_date OR (item->>'end_date')::date > year_row.end_date
           OR (check_active AND NOT year_row.is_active) THEN
            RAISE EXCEPTION 'Semester must fit active academic year' USING ERRCODE='23514';
        END IF;
    WHEN 'program_courses', 'course_offerings' THEN
        SELECT * INTO program_row FROM public.programs p WHERE p.program_id=(item->>'program_id')::uuid;
        SELECT * INTO course_row FROM public.courses c WHERE c.course_id=(item->>'course_id')::uuid;
        owner := public.academic_master_tenant('programs', (item->>'program_id')::uuid);
        parent_owner := public.academic_master_tenant('courses', (item->>'course_id')::uuid);
        IF owner IS DISTINCT FROM parent_owner OR owner IS NULL THEN
            RAISE EXCEPTION 'Program and subject tenant mismatch' USING ERRCODE='23514';
        END IF;
        IF check_active AND (NOT program_row.is_active OR NOT course_row.is_active
            OR NOT EXISTS(SELECT 1 FROM public.departments d WHERE d.department_id=program_row.department_id AND d.is_active)
            OR NOT EXISTS(SELECT 1 FROM public.departments d WHERE d.department_id=course_row.department_id AND d.is_active)) THEN
            RAISE EXCEPTION 'Active program and subject required' USING ERRCODE='23514';
        END IF;
        IF (item->>'semester_id') IS NOT NULL THEN
            SELECT * INTO semester_row FROM public.semesters s WHERE s.semester_id=(item->>'semester_id')::uuid;
            SELECT * INTO year_row FROM public.academic_years y WHERE y.academic_year_id=semester_row.academic_year_id;
            IF year_row.institution_id IS DISTINCT FROM owner OR (check_active AND (NOT semester_row.is_active OR NOT year_row.is_active)) THEN
                RAISE EXCEPTION 'Invalid semester tenant or activity' USING ERRCODE='23514';
            END IF;
        END IF;
        IF TG_TABLE_NAME='course_offerings' THEN
            IF semester_row.academic_year_id IS DISTINCT FROM (item->>'academic_year_id')::uuid THEN
                RAISE EXCEPTION 'Offering year and semester mismatch' USING ERRCODE='23514';
            END IF;
            IF check_active AND NOT EXISTS(SELECT 1 FROM public.program_courses pc WHERE pc.program_id=(item->>'program_id')::uuid AND pc.course_id=(item->>'course_id')::uuid AND pc.is_active AND (pc.semester_id IS NULL OR pc.semester_id=(item->>'semester_id')::uuid)) THEN
                RAISE EXCEPTION 'Active matching curriculum link required' USING ERRCODE='23514';
            END IF;
        END IF;
    WHEN 'sections' THEN
        SELECT * INTO offering_row FROM public.course_offerings o WHERE o.course_offering_id=(item->>'course_offering_id')::uuid;
        owner := public.academic_master_tenant('course_offerings', (item->>'course_offering_id')::uuid);
        IF check_active AND (NOT offering_row.is_active
            OR NOT EXISTS(SELECT 1 FROM public.courses c JOIN public.departments d USING(department_id) WHERE c.course_id=offering_row.course_id AND c.is_active AND d.is_active)
            OR NOT EXISTS(SELECT 1 FROM public.programs p JOIN public.departments d USING(department_id) WHERE p.program_id=offering_row.program_id AND p.is_active AND d.is_active)
            OR NOT EXISTS(SELECT 1 FROM public.semesters s JOIN public.academic_years y USING(academic_year_id) WHERE s.semester_id=offering_row.semester_id AND s.is_active AND y.is_active)) THEN
            RAISE EXCEPTION 'Active offering ancestry required' USING ERRCODE='23514';
        END IF;
    END CASE;
    IF owner IS NULL THEN RAISE EXCEPTION 'Academic parent missing' USING ERRCODE='23514'; END IF;
    IF TG_TABLE_NAME='academic_years' AND TG_OP='UPDATE' THEN
        IF EXISTS(SELECT 1 FROM public.semesters s WHERE s.academic_year_id=(item->>'academic_year_id')::uuid
          AND (s.start_date<(item->>'start_date')::date OR s.end_date>(item->>'end_date')::date)) THEN
            RAISE EXCEPTION 'Year dates exclude existing semesters' USING ERRCODE='23514';
        END IF;
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."validate_academic_master_record"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."validate_test_schedule"("p_tenant" "uuid", "p_section" "uuid", "p_id" "uuid", "p_date" "date", "p_start" time without time zone, "p_end" time without time zone) RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE co public.course_offerings; sec public.sections;
BEGIN
 SELECT * INTO sec FROM sections WHERE section_id=p_section;
 SELECT * INTO co FROM course_offerings WHERE course_offering_id=sec.course_offering_id;
 IF p_date IS NOT NULL AND NOT EXISTS(SELECT 1 FROM semesters s JOIN academic_years y USING(academic_year_id)
   WHERE s.semester_id=co.semester_id AND y.institution_id=p_tenant
     AND p_date BETWEEN s.start_date AND s.end_date AND p_date BETWEEN y.start_date AND y.end_date) THEN
   RAISE EXCEPTION 'Date is outside the academic period' USING ERRCODE='23514';
 END IF;
 IF p_start IS NOT NULL AND EXISTS(SELECT 1 FROM faculty_tests t JOIN sections s ON s.section_id=t.section_id
   JOIN course_offerings o ON o.course_offering_id=s.course_offering_id
   WHERE t.institution_id=p_tenant AND t.test_id IS DISTINCT FROM p_id AND t.status<>'CANCELLED'
     AND o.program_id=co.program_id AND o.academic_year_id=co.academic_year_id AND o.semester_id=co.semester_id
     AND s.code=sec.code AND t.scheduled_date=p_date AND t.start_time<p_end AND t.end_time>p_start) THEN
   RAISE EXCEPTION 'Assessment overlaps another test in this class' USING ERRCODE='23505';
 END IF;
END; $$;


ALTER FUNCTION "public"."validate_test_schedule"("p_tenant" "uuid", "p_section" "uuid", "p_id" "uuid", "p_date" "date", "p_start" time without time zone, "p_end" time without time zone) OWNER TO "postgres";


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
    CONSTRAINT "academic_years_current_active" CHECK (((NOT "is_current") OR "is_active")),
    CONSTRAINT "academic_years_date_check" CHECK (("end_date" > "start_date")),
    CONSTRAINT "academic_years_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0))
);


ALTER TABLE "public"."academic_years" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."admin_audit_log" (
    "audit_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "actor_user_id" "uuid" NOT NULL,
    "action" "text" NOT NULL,
    "table_name" "text",
    "record_id" "text",
    "record_data" "jsonb",
    "ip_address" "inet",
    "user_agent" "text",
    "status" "text" DEFAULT 'success'::"text" NOT NULL,
    "performed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "institution_id" "uuid",
    CONSTRAINT "admin_audit_log_action_not_blank_check" CHECK (("btrim"("action") <> ''::"text")),
    CONSTRAINT "admin_audit_log_status_check" CHECK (("status" = ANY (ARRAY['success'::"text", 'failure'::"text", 'info'::"text"])))
);


ALTER TABLE "public"."admin_audit_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."admin_audit_log" IS 'Audit trail of privileged admin actions';



COMMENT ON COLUMN "public"."admin_audit_log"."institution_id" IS 'Tenant scope for institution audit events; NULL is reserved for platform/global events.';



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


CREATE TABLE IF NOT EXISTS "public"."auth_consumed_password_recovery_sessions" (
    "session_fingerprint" "text" NOT NULL,
    "auth_user_id" "uuid" NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "consumed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "auth_consumed_password_recovery_sessions_fingerprint_check" CHECK (("session_fingerprint" ~ '^[0-9a-f]{64}$'::"text"))
);


ALTER TABLE "public"."auth_consumed_password_recovery_sessions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."auth_security_events" (
    "event_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "auth_user_id" "uuid",
    "event" "text" NOT NULL,
    "status" "text" NOT NULL,
    "ip_address" "inet",
    "user_agent" "text",
    "occurred_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "auth_security_events_event_not_blank_check" CHECK (("btrim"("event") <> ''::"text")),
    CONSTRAINT "auth_security_events_status_check" CHECK (("status" = ANY (ARRAY['success'::"text", 'failure'::"text", 'info'::"text"])))
);


ALTER TABLE "public"."auth_security_events" OWNER TO "postgres";


COMMENT ON TABLE "public"."auth_security_events" IS 'Append-only authentication security event trail; contains no credentials or bearer tokens.';



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


CREATE TABLE IF NOT EXISTS "public"."chunk_embeddings" (
    "chunk_id" "uuid" NOT NULL,
    "model_name" "text" NOT NULL,
    "embedding_dimensions" integer NOT NULL,
    "embedding" "extensions"."vector"(1536) NOT NULL,
    "embedded_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "chunk_embeddings_embedding_dimensions_check" CHECK (("embedding_dimensions" > 0)),
    CONSTRAINT "chunk_embeddings_model_name_check" CHECK (("btrim"("model_name") <> ''::"text"))
);


ALTER TABLE "public"."chunk_embeddings" OWNER TO "postgres";


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
    "embedding_status" "text",
    "embedding_error" "text",
    CONSTRAINT "document_processing_runs_embedding_failed_error_check" CHECK ((("embedding_status" <> 'failed'::"text") OR ("embedding_error" IS NOT NULL))),
    CONSTRAINT "document_processing_runs_embedding_status_check" CHECK ((("embedding_status" IS NULL) OR ("embedding_status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'embedded'::"text", 'failed'::"text"])))),
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
    "extracted_text" "text",
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


CREATE TABLE IF NOT EXISTS "public"."email_delivery_attempts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "outbox_id" "uuid" NOT NULL,
    "attempt_number" integer NOT NULL,
    "started_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    "result" "text" DEFAULT 'processing'::"text" NOT NULL,
    "failure_category" "text",
    "provider_message_id" "text",
    CONSTRAINT "email_delivery_attempts_number_check" CHECK (("attempt_number" > 0)),
    CONSTRAINT "email_delivery_attempts_result_check" CHECK (("result" = ANY (ARRAY['processing'::"text", 'sent'::"text", 'retry'::"text", 'dead_letter'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "public"."email_delivery_attempts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."email_delivery_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "provider_name" "text" NOT NULL,
    "event_key" "text" NOT NULL,
    "replay_token_digest" "text" NOT NULL,
    "provider_event_id" "text" NOT NULL,
    "provider_message_id" "text",
    "event_type" "text" NOT NULL,
    "event_timestamp" timestamp with time zone NOT NULL,
    "outbox_id" "uuid",
    "processing_result" "text" DEFAULT 'received'::"text" NOT NULL,
    "state_changed" boolean DEFAULT false NOT NULL,
    "received_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "processed_at" timestamp with time zone,
    CONSTRAINT "email_delivery_events_digest_check" CHECK ((("length"("event_key") = 64) AND ("length"("replay_token_digest") = 64))),
    CONSTRAINT "email_delivery_events_result_check" CHECK (("processing_result" = ANY (ARRAY['received'::"text", 'applied'::"text", 'no_state_change'::"text", 'stale_generation'::"text", 'unknown_message'::"text", 'unsupported'::"text"])))
);


ALTER TABLE "public"."email_delivery_events" OWNER TO "postgres";


ALTER TABLE "public"."email_outbox" ALTER COLUMN "delivery_sequence" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."email_outbox_delivery_sequence_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."faculty_attendance_import_rows" (
    "import_row_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "import_id" "uuid" NOT NULL,
    "row_number" integer NOT NULL,
    "raw_data" "jsonb" NOT NULL,
    "normalized_data" "jsonb",
    "validation_status" "text" DEFAULT 'ERROR'::"text" NOT NULL,
    "errors" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "warnings" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    CONSTRAINT "faculty_attendance_import_rows_validation_status_check" CHECK (("validation_status" = ANY (ARRAY['VALID'::"text", 'ERROR'::"text", 'DUPLICATE'::"text", 'CONFLICT'::"text", 'UPDATE'::"text", 'NEW'::"text"])))
);


ALTER TABLE "public"."faculty_attendance_import_rows" OWNER TO "postgres";


COMMENT ON TABLE "public"."faculty_attendance_import_rows" IS 'Untrusted staging rows; never authoritative until explicit review/import.';



CREATE TABLE IF NOT EXISTS "public"."faculty_attendance_imports" (
    "import_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "section_id" "uuid" NOT NULL,
    "course_offering_id" "uuid" NOT NULL,
    "academic_year_id" "uuid" NOT NULL,
    "semester_id" "uuid" NOT NULL,
    "uploaded_by" "uuid" NOT NULL,
    "original_filename" "text" NOT NULL,
    "file_type" "text" NOT NULL,
    "processing_strategy" "text" NOT NULL,
    "ai_confirmation_required" boolean DEFAULT false NOT NULL,
    "ai_confirmed_at" timestamp with time zone,
    "status" "text" DEFAULT 'UPLOADED'::"text" NOT NULL,
    "summary" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "test_id" "uuid",
    CONSTRAINT "faculty_attendance_imports_processing_strategy_check" CHECK (("processing_strategy" = ANY (ARRAY['CSV'::"text", 'XLS'::"text", 'XLSX'::"text", 'PDF_TEXT'::"text", 'OCR_AI'::"text"]))),
    CONSTRAINT "faculty_attendance_imports_status_check" CHECK (("status" = ANY (ARRAY['PROCESSING'::"text", 'UPLOADED'::"text", 'VALIDATED'::"text", 'REVIEWED'::"text", 'IMPORTED'::"text", 'PARTIALLY_IMPORTED'::"text", 'FAILED'::"text"])))
);


ALTER TABLE "public"."faculty_attendance_imports" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."faculty_attendance_records" (
    "record_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "roster_id" "uuid" NOT NULL,
    "status" "text" NOT NULL,
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "faculty_attendance_records_status_check" CHECK (("status" = ANY (ARRAY['present'::"text", 'absent'::"text", 'late'::"text", 'excused'::"text"])))
);


ALTER TABLE "public"."faculty_attendance_records" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."faculty_attendance_rosters" (
    "roster_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "section_id" "uuid" NOT NULL,
    "course_offering_id" "uuid" NOT NULL,
    "semester_id" "uuid" NOT NULL,
    "register_number" "text" NOT NULL,
    "university_roll_number" "text",
    "student_name" "text" NOT NULL,
    "email" "text",
    "address" "text",
    "roster_status" "text" DEFAULT 'UNREGISTERED'::"text" NOT NULL,
    "linked_student_id" "uuid",
    "source_metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "imported_summary" "jsonb",
    "created_by" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "reconciliation_state" "text" DEFAULT 'NONE'::"text" NOT NULL,
    "reconciliation_errors" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    CONSTRAINT "faculty_attendance_roster_name_nonblank" CHECK (("btrim"("student_name") <> ''::"text")),
    CONSTRAINT "faculty_attendance_roster_register_nonblank" CHECK (("btrim"("register_number") <> ''::"text")),
    CONSTRAINT "faculty_attendance_rosters_reconciliation_state_check" CHECK (("reconciliation_state" = ANY (ARRAY['NONE'::"text", 'PENDING'::"text", 'LINKED'::"text", 'CONFLICT'::"text"]))),
    CONSTRAINT "faculty_attendance_rosters_roster_status_check" CHECK (("roster_status" = ANY (ARRAY['UNREGISTERED'::"text", 'PENDING_APPROVAL'::"text", 'ACTIVE'::"text", 'INACTIVE'::"text"])))
);


ALTER TABLE "public"."faculty_attendance_rosters" OWNER TO "postgres";


COMMENT ON COLUMN "public"."faculty_attendance_rosters"."imported_summary" IS 'Imported percentage/count summary with provenance; never treated as session records.';



CREATE TABLE IF NOT EXISTS "public"."faculty_attendance_sessions" (
    "session_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "section_id" "uuid" NOT NULL,
    "course_offering_id" "uuid" NOT NULL,
    "session_date" "date" NOT NULL,
    "conducted_by" "uuid" NOT NULL,
    "source_metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."faculty_attendance_sessions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."faculty_responsibilities" (
    "responsibility_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "faculty_user_id" "uuid" NOT NULL,
    "responsibility_code" "text" NOT NULL,
    "scope_type" "text" NOT NULL,
    "scope_id" "uuid" NOT NULL,
    "department_id" "uuid",
    "program_id" "uuid",
    "semester_id" "uuid",
    "academic_year_id" "uuid",
    "section_id" "uuid",
    "section_code" "text",
    "course_id" "uuid",
    "scope_key" "text" NOT NULL,
    "exclusive_scope" boolean DEFAULT true NOT NULL,
    "start_at" timestamp with time zone NOT NULL,
    "end_at" timestamp with time zone,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_by" "uuid" NOT NULL,
    "revoked_at" timestamp with time zone,
    "revoked_by" "uuid",
    CONSTRAINT "faculty_responsibilities_scope_type_check" CHECK (("scope_type" = ANY (ARRAY['institution'::"text", 'department'::"text", 'program'::"text", 'semester'::"text", 'section'::"text", 'course'::"text"]))),
    CONSTRAINT "responsibility_revocation_pair" CHECK ((("revoked_at" IS NULL) = ("revoked_by" IS NULL))),
    CONSTRAINT "responsibility_valid_interval" CHECK ((("end_at" IS NULL) OR ("end_at" > "start_at")))
);


ALTER TABLE "public"."faculty_responsibilities" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."faculty_section_assignments" (
    "assignment_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "faculty_user_id" "uuid" NOT NULL,
    "section_id" "uuid" NOT NULL,
    "assigned_by" "uuid" NOT NULL,
    "assigned_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "revoked_by" "uuid",
    "revoked_at" timestamp with time zone,
    "start_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "end_at" timestamp with time zone,
    "is_active" boolean DEFAULT true NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "faculty_section_assignments_revocation_pair_check" CHECK ((("revoked_by" IS NULL) = ("revoked_at" IS NULL))),
    CONSTRAINT "teaching_valid_interval" CHECK ((("end_at" IS NULL) OR ("end_at" > "start_at")))
);


ALTER TABLE "public"."faculty_section_assignments" OWNER TO "postgres";


COMMENT ON TABLE "public"."faculty_section_assignments" IS 'Phase 8.1 active Faculty-to-section assignments; institution is validated against the offering department.';



CREATE TABLE IF NOT EXISTS "public"."faqs" (
    "faq_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid",
    "category" "text" DEFAULT 'general'::"text" NOT NULL,
    "question" "text" NOT NULL,
    "answer" "text" NOT NULL,
    "display_order" integer DEFAULT 0 NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "is_published" boolean DEFAULT false NOT NULL,
    CONSTRAINT "faqs_answer_not_blank_check" CHECK (("btrim"("answer") <> ''::"text")),
    CONSTRAINT "faqs_display_order_check" CHECK (("display_order" >= 0)),
    CONSTRAINT "faqs_question_not_blank_check" CHECK (("btrim"("question") <> ''::"text"))
);


ALTER TABLE "public"."faqs" OWNER TO "postgres";


COMMENT ON TABLE "public"."faqs" IS 'Frequently-asked-questions (global or per-institution)';



CREATE TABLE IF NOT EXISTS "public"."institution_join_requests" (
    "join_request_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "requested_institution_code" "text" NOT NULL,
    "requested_by_user_id" "uuid" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "decision_reason" "text",
    "decided_by_user_id" "uuid",
    "decided_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "institution_join_requests_code_check" CHECK ((("requested_institution_code" = "upper"("btrim"("requested_institution_code"))) AND ("btrim"("requested_institution_code") <> ''::"text"))),
    CONSTRAINT "institution_join_requests_decision_check" CHECK (((("status" = 'pending'::"text") AND ("decided_by_user_id" IS NULL) AND ("decided_at" IS NULL)) OR (("status" <> 'pending'::"text") AND ("decided_by_user_id" IS NOT NULL) AND ("decided_at" IS NOT NULL)))),
    CONSTRAINT "institution_join_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'rejected'::"text"])))
);


ALTER TABLE "public"."institution_join_requests" OWNER TO "postgres";


COMMENT ON TABLE "public"."institution_join_requests" IS 'Phase 6.13 institution-to-organization join requests. Approval by an organization-scoped admin is the only way an institution becomes active.';



CREATE TABLE IF NOT EXISTS "public"."institution_membership_requests" (
    "request_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "requested_role" "text" NOT NULL,
    "official_email" "text" NOT NULL,
    "full_name" "text",
    "designation" "text",
    "department" "text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "decision_reason" "text",
    "decided_by_user_id" "uuid",
    "decided_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "institution_membership_requests_decision_check" CHECK (((("status" = 'pending'::"text") AND ("decided_by_user_id" IS NULL) AND ("decided_at" IS NULL)) OR (("status" <> 'pending'::"text") AND ("decided_by_user_id" IS NOT NULL) AND ("decided_at" IS NOT NULL)))),
    CONSTRAINT "institution_membership_requests_email_check" CHECK (("official_email" = "btrim"("lower"("official_email")))),
    CONSTRAINT "institution_membership_requests_role_check" CHECK (("requested_role" = ANY (ARRAY['staff'::"text", 'faculty'::"text"]))),
    CONSTRAINT "institution_membership_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'rejected'::"text"])))
);


ALTER TABLE "public"."institution_membership_requests" OWNER TO "postgres";


COMMENT ON TABLE "public"."institution_membership_requests" IS 'Phase 6.13 staff/faculty onboarding requests. Approval by an authorized admin is the ONLY path that grants the role; the request row never grants access by itself.';



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
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "display_name" "text",
    "logo_url" "text",
    "primary_color" "text",
    "secondary_color" "text",
    "welcome_message" "text",
    CONSTRAINT "institutions_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'active'::"text", 'suspended'::"text", 'rejected'::"text"])))
);


ALTER TABLE "public"."institutions" OWNER TO "postgres";


COMMENT ON COLUMN "public"."institutions"."organization_id" IS 'Owning organization (Phase 6.13). NOT NULL: every institution belongs to exactly one organization.';



COMMENT ON COLUMN "public"."institutions"."status" IS 'Authoritative lifecycle status (Phase 6.13). Derived flag is_active is kept in sync by trigger trg_phase613_institutions_status.';



COMMENT ON COLUMN "public"."institutions"."display_name" IS 'Phase 7.13 optional branding: public display name (falls back to name).';



COMMENT ON COLUMN "public"."institutions"."logo_url" IS 'Phase 7.13 optional branding: public logo image URL.';



COMMENT ON COLUMN "public"."institutions"."primary_color" IS 'Phase 7.13 optional branding: primary accent colour (CSS hex).';



COMMENT ON COLUMN "public"."institutions"."secondary_color" IS 'Phase 7.13 optional branding: secondary accent colour (CSS hex).';



COMMENT ON COLUMN "public"."institutions"."welcome_message" IS 'Phase 7.13 optional branding: public gateway welcome message.';



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
    "visibility" "text" DEFAULT 'restricted'::"text" NOT NULL,
    CONSTRAINT "knowledge_sources_authority_level_check" CHECK (("btrim"("authority_level") <> ''::"text")),
    CONSTRAINT "knowledge_sources_effective_dates_check" CHECK ((("effective_until" IS NULL) OR ("effective_from" IS NULL) OR ("effective_until" >= "effective_from"))),
    CONSTRAINT "knowledge_sources_lifecycle_status_check" CHECK (("lifecycle_status" = ANY (ARRAY['draft'::"text", 'under_review'::"text", 'approved'::"text", 'published'::"text", 'archived'::"text", 'superseded'::"text"]))),
    CONSTRAINT "knowledge_sources_source_type_check" CHECK (("btrim"("source_type") <> ''::"text")),
    CONSTRAINT "knowledge_sources_visibility_check" CHECK (("visibility" = ANY (ARRAY['public'::"text", 'authenticated'::"text", 'restricted'::"text"])))
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


CREATE TABLE IF NOT EXISTS "public"."notices" (
    "notice_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid",
    "title" "text" NOT NULL,
    "content" "text" NOT NULL,
    "category" "text" DEFAULT 'general'::"text" NOT NULL,
    "priority" "text" DEFAULT 'normal'::"text" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "is_pinned" boolean DEFAULT false NOT NULL,
    "published_at" timestamp with time zone,
    "expires_at" timestamp with time zone,
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "is_published" boolean DEFAULT false NOT NULL,
    CONSTRAINT "notices_category_check" CHECK (("category" = ANY (ARRAY['general'::"text", 'academic'::"text", 'event'::"text", 'holiday'::"text", 'exam'::"text", 'other'::"text"]))),
    CONSTRAINT "notices_content_not_blank_check" CHECK (("btrim"("content") <> ''::"text")),
    CONSTRAINT "notices_priority_check" CHECK (("priority" = ANY (ARRAY['low'::"text", 'normal'::"text", 'high'::"text", 'urgent'::"text"]))),
    CONSTRAINT "notices_title_not_blank_check" CHECK (("btrim"("title") <> ''::"text"))
);


ALTER TABLE "public"."notices" OWNER TO "postgres";


COMMENT ON TABLE "public"."notices" IS 'Notice / announcement board entries';



CREATE TABLE IF NOT EXISTS "public"."organizations" (
    "organization_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "organization_code" "text" NOT NULL,
    "official_email" "text" NOT NULL,
    "contact_information" "text" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "join_code" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "organizations_code_check" CHECK ((("organization_code" = "upper"("btrim"("organization_code"))) AND ("btrim"("organization_code") <> ''::"text"))),
    CONSTRAINT "organizations_contact_check" CHECK (("btrim"("contact_information") <> ''::"text")),
    CONSTRAINT "organizations_email_check" CHECK (("official_email" = "btrim"("lower"("official_email")))),
    CONSTRAINT "organizations_join_code_check" CHECK ((("join_code" IS NULL) OR ("btrim"("join_code") <> ''::"text"))),
    CONSTRAINT "organizations_name_check" CHECK (("btrim"("name") <> ''::"text")),
    CONSTRAINT "organizations_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'active'::"text", 'suspended'::"text", 'rejected'::"text"])))
);


ALTER TABLE "public"."organizations" OWNER TO "postgres";


COMMENT ON TABLE "public"."organizations" IS 'Top-level tenant group (Phase 6.13). An organization owns 1..n institutions.';



CREATE TABLE IF NOT EXISTS "public"."permissions" (
    "permission_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
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


CREATE TABLE IF NOT EXISTS "public"."platform_admin_invitations" (
    "invitation_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "email" "text" NOT NULL,
    "token_hash" "text" NOT NULL,
    "role_name" "text" DEFAULT 'admin'::"text" NOT NULL,
    "status" "text" DEFAULT 'invited'::"text" NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "accepted_at" timestamp with time zone,
    "cancelled_at" timestamp with time zone,
    "accepted_user_id" "uuid",
    "created_by" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "email_verified_at" timestamp with time zone,
    "email_delivery_status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "email_delivery_at" timestamp with time zone,
    "email_delivery_attempts" integer DEFAULT 0 NOT NULL,
    "last_sent_at" timestamp with time zone,
    "resend_count" integer DEFAULT 0 NOT NULL,
    CONSTRAINT "platform_admin_invitations_delivery_attempts_check" CHECK (("email_delivery_attempts" >= 0)),
    CONSTRAINT "platform_admin_invitations_email_check" CHECK ((("btrim"("email") <> ''::"text") AND ("email" = "lower"("btrim"("email"))) AND ("length"("email") <= 320))),
    CONSTRAINT "platform_admin_invitations_email_delivery_status_check" CHECK (("email_delivery_status" = ANY (ARRAY['pending'::"text", 'sent'::"text", 'delivered'::"text", 'failed'::"text"]))),
    CONSTRAINT "platform_admin_invitations_expiry_check" CHECK (("expires_at" > "created_at")),
    CONSTRAINT "platform_admin_invitations_resend_count_check" CHECK (("resend_count" >= 0)),
    CONSTRAINT "platform_admin_invitations_role_name_check" CHECK (("role_name" = ANY (ARRAY['admin'::"text", 'staff'::"text", 'faculty'::"text"]))),
    CONSTRAINT "platform_admin_invitations_status_check" CHECK (("status" = ANY (ARRAY['invited'::"text", 'accepted'::"text", 'cancelled'::"text", 'expired'::"text"]))),
    CONSTRAINT "platform_admin_invitations_terminal_state_check" CHECK (((("status" = 'invited'::"text") AND ("accepted_at" IS NULL) AND ("cancelled_at" IS NULL) AND ("accepted_user_id" IS NULL)) OR (("status" = 'accepted'::"text") AND ("accepted_at" IS NOT NULL) AND ("cancelled_at" IS NULL)) OR (("status" = 'cancelled'::"text") AND ("cancelled_at" IS NOT NULL) AND ("accepted_at" IS NULL)) OR (("status" = 'expired'::"text") AND ("accepted_at" IS NULL) AND ("cancelled_at" IS NULL)))),
    CONSTRAINT "platform_admin_invitations_token_hash_check" CHECK (("token_hash" ~ '^[0-9a-f]{64}$'::"text")),
    CONSTRAINT "platform_admin_invitations_verified_requires_accepted_check" CHECK ((("email_verified_at" IS NULL) OR (("status" = 'accepted'::"text") AND ("accepted_at" IS NOT NULL))))
);


ALTER TABLE "public"."platform_admin_invitations" OWNER TO "postgres";


COMMENT ON TABLE "public"."platform_admin_invitations" IS 'Generic institution-role invitations. Server-owned role_name is limited to admin, staff, or faculty; raw tokens are never stored.';



COMMENT ON COLUMN "public"."platform_admin_invitations"."email_verified_at" IS 'Phase 7.15: set by the server only, after acceptance proved the Auth account carries exactly this invitation''s email. Never client-asserted.';



COMMENT ON COLUMN "public"."platform_admin_invitations"."email_delivery_status" IS 'Phase 7.15: pending | sent | failed. Bookkeeping about delivery attempts only - never a lifecycle state.';



CREATE TABLE IF NOT EXISTS "public"."platform_institution_audit_log" (
    "audit_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "actor_user_id" "uuid" NOT NULL,
    "action" "text" NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "target_user_id" "uuid",
    "result" "text" DEFAULT 'success'::"text" NOT NULL,
    "details" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "performed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "platform_institution_audit_action_check" CHECK (("action" = ANY (ARRAY['institution_created'::"text", 'institution_updated'::"text", 'institution_suspended'::"text", 'institution_activated'::"text", 'admin_assigned'::"text", 'institution_admin_invited'::"text", 'institution_admin_invitation_accepted'::"text", 'institution_admin_invitation_expired'::"text", 'institution_admin_invitation_cancelled'::"text", 'institution_admin_revoked'::"text", 'institution_admin_invitation_email_sent'::"text", 'institution_admin_invitation_email_failed'::"text", 'institution_admin_invitation_resent'::"text", 'institution_admin_invitation_verified'::"text"]))),
    CONSTRAINT "platform_institution_audit_result_check" CHECK (("result" = ANY (ARRAY['success'::"text", 'already_applied'::"text", 'denied'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."platform_institution_audit_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."platform_institution_audit_log" IS 'Phase 7.13 service-role-only audit ledger for Super Admin institution management.';



COMMENT ON CONSTRAINT "platform_institution_audit_action_check" ON "public"."platform_institution_audit_log" IS 'Phase 7.15: institution CRUD + University Admin invitation lifecycle + invitation delivery/verification vocabulary. No credential material is representable.';



CREATE TABLE IF NOT EXISTS "public"."platform_role_audit_log" (
    "audit_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "actor_identifier" "text" NOT NULL,
    "action" "text" NOT NULL,
    "target_user_id" "uuid" NOT NULL,
    "role_name" "text" NOT NULL,
    "result" "text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "performed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "platform_role_audit_log_action_check" CHECK (("action" = ANY (ARRAY['assign'::"text", 'revoke'::"text"]))),
    CONSTRAINT "platform_role_audit_log_actor_check" CHECK ((("btrim"("actor_identifier") <> ''::"text") AND ("length"("actor_identifier") <= 200))),
    CONSTRAINT "platform_role_audit_log_result_check" CHECK (("result" = ANY (ARRAY['assigned'::"text", 'already_assigned'::"text", 'revoked'::"text", 'already_revoked'::"text"]))),
    CONSTRAINT "platform_role_audit_log_role_check" CHECK (("role_name" = 'super_admin'::"text"))
);


ALTER TABLE "public"."platform_role_audit_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."platform_role_audit_log" IS 'Phase 7.12 audit ledger for controlled super_admin assignment and revocation.';



CREATE TABLE IF NOT EXISTS "public"."platform_super_admin_invitations" (
    "invitation_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "email" "text" NOT NULL,
    "token_hash" "text" NOT NULL,
    "status" "text" DEFAULT 'invited'::"text" NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "created_by" "uuid" NOT NULL,
    "accepted_user_id" "uuid",
    "accepted_at" timestamp with time zone,
    "cancelled_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "platform_super_admin_invitations_email_check" CHECK ((("email" = "lower"("btrim"("email"))) AND ("length"("email") <= 320))),
    CONSTRAINT "platform_super_admin_invitations_status_check" CHECK (("status" = ANY (ARRAY['invited'::"text", 'accepted'::"text", 'cancelled'::"text", 'expired'::"text"])))
);


ALTER TABLE "public"."platform_super_admin_invitations" OWNER TO "postgres";


COMMENT ON TABLE "public"."platform_super_admin_invitations" IS 'Phase 9 single-use invitations for creating additional Super Admin accounts.';



CREATE TABLE IF NOT EXISTS "public"."program_courses" (
    "program_course_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "program_id" "uuid" NOT NULL,
    "course_id" "uuid" NOT NULL,
    "course_type" "text" NOT NULL,
    "is_required" boolean DEFAULT true NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "semester_number" integer,
    "semester_id" "uuid",
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


CREATE TABLE IF NOT EXISTS "public"."responsibility_definitions" (
    "code" "text" NOT NULL,
    "name" "text" NOT NULL,
    "allowed_scope_types" "text"[] NOT NULL,
    "exclusive_scope" boolean DEFAULT true NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    CONSTRAINT "responsibility_definitions_code_check" CHECK (("btrim"("code") <> ''::"text"))
);


ALTER TABLE "public"."responsibility_definitions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."responsibility_permissions" (
    "responsibility_code" "text" NOT NULL,
    "permission_id" "uuid" NOT NULL
);


ALTER TABLE "public"."responsibility_permissions" OWNER TO "postgres";


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
    CONSTRAINT "academic_semesters_current_active" CHECK (((NOT "is_current") OR "is_active")),
    CONSTRAINT "semesters_code_check" CHECK (("length"(TRIM(BOTH FROM "code")) > 0)),
    CONSTRAINT "semesters_date_check" CHECK (("end_date" > "start_date")),
    CONSTRAINT "semesters_name_check" CHECK (("length"(TRIM(BOTH FROM "name")) > 0)),
    CONSTRAINT "semesters_number_check" CHECK (("semester_number" > 0))
);


ALTER TABLE "public"."semesters" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."student_attendance" (
    "student_attendance_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id" "uuid" NOT NULL,
    "section_id" "uuid" NOT NULL,
    "academic_year_id" "uuid" NOT NULL,
    "semester_id" "uuid" NOT NULL,
    "date" "date" NOT NULL,
    "status" "text" NOT NULL,
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "student_attendance_status_check" CHECK (("status" = ANY (ARRAY['present'::"text", 'absent'::"text", 'late'::"text", 'excused'::"text"]))),
    CONSTRAINT "student_attendance_status_not_blank_check" CHECK (("btrim"("status") <> ''::"text"))
);


ALTER TABLE "public"."student_attendance" OWNER TO "postgres";


COMMENT ON TABLE "public"."student_attendance" IS 'Daily attendance records per student-section';



COMMENT ON COLUMN "public"."student_attendance"."institution_id" IS 'Canonical tenant key denormalized onto the attendance row. Always equals students.institution_id; maintained by the student_attendance_tenant_guard trigger and never trusted from the client.';



COMMENT ON COLUMN "public"."student_attendance"."updated_at" IS 'Last modification timestamp, refreshed by the student_attendance_tenant_guard trigger on UPDATE.';



CREATE TABLE IF NOT EXISTS "public"."student_notifications" (
    "notification_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id" "uuid" NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "notification_type" character varying(32) NOT NULL,
    "title" character varying(255) NOT NULL,
    "message" "text" NOT NULL,
    "is_read" boolean DEFAULT false NOT NULL,
    "source_type" character varying(64) DEFAULT 'academic_event'::character varying NOT NULL,
    "source_record_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "read_at" timestamp with time zone,
    CONSTRAINT "student_notifications_notification_type_check" CHECK ((("notification_type")::"text" = ANY ((ARRAY['attendance_alert'::character varying, 'result_published'::character varying, 'academic_status'::character varying, 'academic_admin'::character varying])::"text"[])))
);


ALTER TABLE "public"."student_notifications" OWNER TO "postgres";


COMMENT ON TABLE "public"."student_notifications" IS 'Student notifications and academic alerts (Phase 6.11)';



CREATE TABLE IF NOT EXISTS "public"."student_result_items" (
    "student_result_item_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "student_result_id" "uuid" NOT NULL,
    "course_id" "uuid" NOT NULL,
    "section_id" "uuid",
    "credits_earned" numeric(5,2),
    "credits_max" numeric(5,2),
    "grade_points" numeric(5,2),
    "letter_grade" "text",
    "grade_value" numeric(5,2),
    "status" "text" DEFAULT 'completed'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "student_result_items_credits_check" CHECK ((("credits_earned" IS NULL) OR ("credits_earned" >= (0)::numeric))),
    CONSTRAINT "student_result_items_grade_points_check" CHECK ((("grade_points" IS NULL) OR ("grade_points" >= (0)::numeric))),
    CONSTRAINT "student_result_items_status_check" CHECK (("status" = ANY (ARRAY['completed'::"text", 'incomplete'::"text", 'withdrawn'::"text", 'not_attempted'::"text"])))
);


ALTER TABLE "public"."student_result_items" OWNER TO "postgres";


COMMENT ON TABLE "public"."student_result_items" IS 'Individual course-grade rows within a student_result';



CREATE TABLE IF NOT EXISTS "public"."student_results" (
    "student_result_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id" "uuid" NOT NULL,
    "academic_year_id" "uuid" NOT NULL,
    "semester_id" "uuid" NOT NULL,
    "program_id" "uuid" NOT NULL,
    "result_type" "text" NOT NULL,
    "total_credits_earned" numeric(6,2),
    "total_credits_max" numeric(6,2),
    "sgpa" numeric(4,2),
    "cgpa" numeric(4,2),
    "status" "text" DEFAULT 'published'::"text" NOT NULL,
    "issued_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    CONSTRAINT "student_results_cgpa_check" CHECK ((("cgpa" IS NULL) OR ("cgpa" >= (0)::numeric))),
    CONSTRAINT "student_results_credits_check" CHECK ((("total_credits_earned" IS NULL) OR ("total_credits_earned" >= (0)::numeric))),
    CONSTRAINT "student_results_credits_earned_max_check" CHECK ((("total_credits_earned" IS NULL) OR ("total_credits_max" IS NULL) OR ("total_credits_earned" <= "total_credits_max"))),
    CONSTRAINT "student_results_result_type_check" CHECK (("result_type" = ANY (ARRAY['semester'::"text", 'supplementary'::"text", 'final'::"text", 'provisional'::"text"]))),
    CONSTRAINT "student_results_sgpa_check" CHECK ((("sgpa" IS NULL) OR ("sgpa" >= (0)::numeric))),
    CONSTRAINT "student_results_status_check" CHECK (("status" = ANY (ARRAY['draft'::"text", 'published'::"text", 'withheld'::"text"])))
);


ALTER TABLE "public"."student_results" OWNER TO "postgres";


COMMENT ON TABLE "public"."student_results" IS 'Consolidated per-semester result summary';



COMMENT ON COLUMN "public"."student_results"."institution_id" IS 'Canonical tenant key denormalized onto the result row. Always equals students.institution_id; maintained by the student_results_tenant_guard trigger and never trusted from the client.';



CREATE TABLE IF NOT EXISTS "public"."students" (
    "student_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "student_number" "text" NOT NULL,
    "program_id" "uuid",
    "academic_year_id" "uuid",
    "enrollment_date" "date" NOT NULL,
    "expected_graduation_date" "date",
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "email" "text",
    "register_number" "text",
    "university_roll_number" "text",
    "approval_status" "text" DEFAULT 'pending'::"text" NOT NULL,
    CONSTRAINT "students_approval_status_check" CHECK (("approval_status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'rejected'::"text"]))),
    CONSTRAINT "students_email_check" CHECK ((("email" IS NULL) OR ("email" = "btrim"("lower"("email"))))),
    CONSTRAINT "students_graduation_date_check" CHECK ((("expected_graduation_date" IS NULL) OR ("expected_graduation_date" >= "enrollment_date"))),
    CONSTRAINT "students_register_number_check" CHECK ((("register_number" IS NULL) OR ("btrim"("register_number") <> ''::"text"))),
    CONSTRAINT "students_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'inactive'::"text", 'graduated'::"text", 'withdrawn'::"text"]))),
    CONSTRAINT "students_student_number_check" CHECK (("btrim"("student_number") <> ''::"text")),
    CONSTRAINT "students_university_roll_number_check" CHECK ((("university_roll_number" IS NULL) OR ("btrim"("university_roll_number") <> ''::"text")))
);


ALTER TABLE "public"."students" OWNER TO "postgres";


COMMENT ON TABLE "public"."students" IS 'Student academic profile linked one-to-one to public.users';



COMMENT ON COLUMN "public"."students"."email" IS 'Institutional student email identity (lowercase); institution-scoped unique. Account-level login email uniqueness is owned by public.users.email and Supabase Auth.';



COMMENT ON COLUMN "public"."students"."register_number" IS 'Institution-assigned register number; unique within institution_id.';



COMMENT ON COLUMN "public"."students"."university_roll_number" IS 'University-assigned roll number; unique within institution_id.';



COMMENT ON COLUMN "public"."students"."approval_status" IS 'Registration lifecycle state (pending/approved/rejected); independent of the academic status and is_active fields.';



CREATE TABLE IF NOT EXISTS "public"."test_results" (
    "test_result_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "student_id" "uuid",
    "course_id" "uuid" NOT NULL,
    "section_id" "uuid",
    "academic_year_id" "uuid" NOT NULL,
    "semester_id" "uuid" NOT NULL,
    "test_name" "text" NOT NULL,
    "test_type" "text" NOT NULL,
    "max_marks" numeric(8,2) NOT NULL,
    "scored_marks" numeric(8,2),
    "percentage" numeric(5,2),
    "letter_grade" "text",
    "conducted_at" timestamp with time zone,
    "status" "text" DEFAULT 'published'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "test_id" "uuid",
    "roster_id" "uuid",
    "mark_status" "text",
    "remarks" "text",
    CONSTRAINT "test_results_explicit_score" CHECK ((("test_id" IS NULL) OR ((("mark_status" = 'present'::"text") AND ("scored_marks" IS NOT NULL)) OR (("mark_status" <> 'present'::"text") AND ("scored_marks" IS NULL))))),
    CONSTRAINT "test_results_identity" CHECK (((("test_id" IS NULL) AND ("roster_id" IS NULL) AND ("student_id" IS NOT NULL)) OR (("test_id" IS NOT NULL) AND ("roster_id" IS NOT NULL) AND ("mark_status" IS NOT NULL)))),
    CONSTRAINT "test_results_mark_status_check" CHECK (("mark_status" = ANY (ARRAY['present'::"text", 'absent'::"text", 'exempt'::"text", 'not_attempted'::"text", 'missing'::"text"]))),
    CONSTRAINT "test_results_max_marks_check" CHECK (("max_marks" > (0)::numeric)),
    CONSTRAINT "test_results_percentage_check" CHECK ((("percentage" IS NULL) OR (("percentage" >= (0)::numeric) AND ("percentage" <= (100)::numeric)))),
    CONSTRAINT "test_results_remarks_check" CHECK (("length"("remarks") <= 1000)),
    CONSTRAINT "test_results_score_marks_check" CHECK ((("scored_marks" IS NULL) OR ("scored_marks" <= "max_marks"))),
    CONSTRAINT "test_results_scored_marks_check" CHECK ((("scored_marks" IS NULL) OR ("scored_marks" >= (0)::numeric))),
    CONSTRAINT "test_results_status_check" CHECK (("status" = ANY (ARRAY['draft'::"text", 'published'::"text", 'withheld'::"text"]))),
    CONSTRAINT "test_results_test_name_check" CHECK (("btrim"("test_name") <> ''::"text"))
);


ALTER TABLE "public"."test_results" OWNER TO "postgres";


COMMENT ON TABLE "public"."test_results" IS 'Per-test / per-exam scores for a student';



COMMENT ON COLUMN "public"."test_results"."institution_id" IS 'Canonical tenant key denormalized onto the result row. Always equals students.institution_id; maintained by the test_results_tenant_guard trigger and never trusted from the client.';



CREATE TABLE IF NOT EXISTS "public"."test_types" (
    "code" "text" NOT NULL,
    "name" "text" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    CONSTRAINT "test_types_code_check" CHECK (("code" ~ '^[a-z][a-z0-9_]{0,39}$'::"text"))
);


ALTER TABLE "public"."test_types" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_permission_grants" (
    "grant_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "institution_id" "uuid" NOT NULL,
    "permission_id" "uuid" NOT NULL,
    "granted_by" "uuid" NOT NULL,
    "granted_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "revoked_by" "uuid",
    "revoked_at" timestamp with time zone,
    CONSTRAINT "user_permission_grants_revocation_pair_check" CHECK ((("revoked_by" IS NULL) = ("revoked_at" IS NULL)))
);


ALTER TABLE "public"."user_permission_grants" OWNER TO "postgres";


COMMENT ON TABLE "public"."user_permission_grants" IS 'Phase 8.1 additive, institution-scoped direct permissions for eligible Staff only; revocations retain history.';



CREATE TABLE IF NOT EXISTS "public"."user_roles" (
    "user_id" "uuid" NOT NULL,
    "role_id" "uuid" NOT NULL,
    "assigned_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "scope_type" "text" DEFAULT 'platform'::"text" NOT NULL,
    "scope_id" "uuid",
    "scope_organization_id" "uuid",
    CONSTRAINT "user_roles_scope_check" CHECK (((("scope_type" = 'platform'::"text") AND ("scope_id" IS NULL) AND ("scope_organization_id" IS NULL)) OR (("scope_type" = 'organization'::"text") AND ("scope_id" IS NOT NULL) AND ("scope_organization_id" = "scope_id")) OR (("scope_type" = 'institution'::"text") AND ("scope_id" IS NOT NULL) AND ("scope_organization_id" IS NOT NULL))))
);


ALTER TABLE "public"."user_roles" OWNER TO "postgres";


COMMENT ON COLUMN "public"."user_roles"."scope_type" IS 'Phase 6.13 authorization scope: platform | organization | institution.';



COMMENT ON COLUMN "public"."user_roles"."scope_id" IS 'Phase 6.13 scope target id: organization_id for organization scope, institution_id for institution scope.';



COMMENT ON COLUMN "public"."user_roles"."scope_organization_id" IS 'Phase 6.13 denormalized parent organization used for organization-bound authorization.';



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
    ADD CONSTRAINT "academic_years_active_dates_exclusion" EXCLUDE USING "gist" ("institution_id" WITH =, "daterange"("start_date", "end_date", '[]'::"text") WITH &&) WHERE ("is_active");



ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_institution_id_code_key" UNIQUE ("institution_id", "code");



ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_pkey" PRIMARY KEY ("academic_year_id");



ALTER TABLE ONLY "public"."admin_audit_log"
    ADD CONSTRAINT "admin_audit_log_pkey" PRIMARY KEY ("audit_id");



ALTER TABLE ONLY "public"."ai_responses"
    ADD CONSTRAINT "ai_responses_message_id_key" UNIQUE ("message_id");



ALTER TABLE ONLY "public"."ai_responses"
    ADD CONSTRAINT "ai_responses_pkey" PRIMARY KEY ("ai_response_id");



ALTER TABLE ONLY "public"."auth_consumed_password_recovery_sessions"
    ADD CONSTRAINT "auth_consumed_password_recovery_sessions_pkey" PRIMARY KEY ("session_fingerprint");



ALTER TABLE ONLY "public"."auth_security_events"
    ADD CONSTRAINT "auth_security_events_pkey" PRIMARY KEY ("event_id");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_institution_id_campus_id_key" UNIQUE ("institution_id", "campus_id");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_institution_id_code_key" UNIQUE ("institution_id", "code");



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_pkey" PRIMARY KEY ("campus_id");



ALTER TABLE ONLY "public"."chunk_embeddings"
    ADD CONSTRAINT "chunk_embeddings_pkey" PRIMARY KEY ("chunk_id", "model_name");



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



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "duplicate_faculty_responsibility" EXCLUDE USING "gist" ("institution_id" WITH =, "faculty_user_id" WITH =, "responsibility_code" WITH =, "scope_type" WITH =, "scope_key" WITH =, "tstzrange"("start_at", "end_at", '[)'::"text") WITH &&) WHERE (("is_active" AND ("revoked_at" IS NULL)));



ALTER TABLE ONLY "public"."email_delivery_attempts"
    ADD CONSTRAINT "email_delivery_attempts_outbox_number_key" UNIQUE ("outbox_id", "attempt_number");



ALTER TABLE ONLY "public"."email_delivery_attempts"
    ADD CONSTRAINT "email_delivery_attempts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."email_delivery_events"
    ADD CONSTRAINT "email_delivery_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."email_delivery_events"
    ADD CONSTRAINT "email_delivery_events_provider_key_key" UNIQUE ("provider_name", "event_key");



ALTER TABLE ONLY "public"."email_delivery_events"
    ADD CONSTRAINT "email_delivery_events_replay_token_key" UNIQUE ("provider_name", "replay_token_digest");



ALTER TABLE ONLY "public"."email_outbox"
    ADD CONSTRAINT "email_outbox_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "exclusive_faculty_responsibility" EXCLUDE USING "gist" ("institution_id" WITH =, "responsibility_code" WITH =, "scope_type" WITH =, "scope_key" WITH =, "tstzrange"("start_at", "end_at", '[)'::"text") WITH &&) WHERE (("is_active" AND ("revoked_at" IS NULL) AND "exclusive_scope"));



ALTER TABLE ONLY "public"."faculty_attendance_import_rows"
    ADD CONSTRAINT "faculty_attendance_import_rows_import_id_row_number_key" UNIQUE ("import_id", "row_number");



ALTER TABLE ONLY "public"."faculty_attendance_import_rows"
    ADD CONSTRAINT "faculty_attendance_import_rows_pkey" PRIMARY KEY ("import_row_id");



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_pkey" PRIMARY KEY ("import_id");



ALTER TABLE ONLY "public"."faculty_attendance_records"
    ADD CONSTRAINT "faculty_attendance_records_pkey" PRIMARY KEY ("record_id");



ALTER TABLE ONLY "public"."faculty_attendance_records"
    ADD CONSTRAINT "faculty_attendance_records_session_id_roster_id_key" UNIQUE ("session_id", "roster_id");



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_institution_id_section_id_regist_key" UNIQUE ("institution_id", "section_id", "register_number");



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_institution_id_section_id_univer_key" UNIQUE ("institution_id", "section_id", "university_roll_number");



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_pkey" PRIMARY KEY ("roster_id");



ALTER TABLE ONLY "public"."faculty_attendance_sessions"
    ADD CONSTRAINT "faculty_attendance_sessions_pkey" PRIMARY KEY ("session_id");



ALTER TABLE ONLY "public"."faculty_attendance_sessions"
    ADD CONSTRAINT "faculty_attendance_sessions_section_id_session_date_key" UNIQUE ("section_id", "session_date");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_pkey" PRIMARY KEY ("responsibility_id");



ALTER TABLE ONLY "public"."faculty_section_assignments"
    ADD CONSTRAINT "faculty_section_assignments_pkey" PRIMARY KEY ("assignment_id");



ALTER TABLE ONLY "public"."faculty_tests"
    ADD CONSTRAINT "faculty_tests_pkey" PRIMARY KEY ("test_id");



ALTER TABLE ONLY "public"."faqs"
    ADD CONSTRAINT "faqs_pkey" PRIMARY KEY ("faq_id");



ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_pkey" PRIMARY KEY ("join_request_id");



ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_pkey" PRIMARY KEY ("request_id");



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



ALTER TABLE ONLY "public"."notices"
    ADD CONSTRAINT "notices_pkey" PRIMARY KEY ("notice_id");



ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_join_code_key" UNIQUE ("join_code");



ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_organization_code_key" UNIQUE ("organization_code");



ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_pkey" PRIMARY KEY ("organization_id");



ALTER TABLE ONLY "public"."permissions"
    ADD CONSTRAINT "permissions_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."permissions"
    ADD CONSTRAINT "permissions_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."permissions"
    ADD CONSTRAINT "permissions_pkey" PRIMARY KEY ("permission_id");



ALTER TABLE ONLY "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_pkey" PRIMARY KEY ("invitation_id");



ALTER TABLE ONLY "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_token_hash_key" UNIQUE ("token_hash");



ALTER TABLE ONLY "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_log_pkey" PRIMARY KEY ("audit_id");



ALTER TABLE ONLY "public"."platform_role_audit_log"
    ADD CONSTRAINT "platform_role_audit_log_pkey" PRIMARY KEY ("audit_id");



ALTER TABLE ONLY "public"."platform_super_admin_invitations"
    ADD CONSTRAINT "platform_super_admin_invitations_pkey" PRIMARY KEY ("invitation_id");



ALTER TABLE ONLY "public"."platform_super_admin_invitations"
    ADD CONSTRAINT "platform_super_admin_invitations_token_hash_key" UNIQUE ("token_hash");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_pkey" PRIMARY KEY ("program_course_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_program_id_course_id_key" UNIQUE ("program_id", "course_id");



ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_department_id_code_key" UNIQUE ("department_id", "code");



ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_pkey" PRIMARY KEY ("program_id");



ALTER TABLE ONLY "public"."responsibility_definitions"
    ADD CONSTRAINT "responsibility_definitions_pkey" PRIMARY KEY ("code");



ALTER TABLE ONLY "public"."responsibility_permissions"
    ADD CONSTRAINT "responsibility_permissions_pkey" PRIMARY KEY ("responsibility_code", "permission_id");



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



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_pkey" PRIMARY KEY ("student_attendance_id");



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_student_section_date_key" UNIQUE ("student_id", "section_id", "date");



ALTER TABLE ONLY "public"."student_notifications"
    ADD CONSTRAINT "student_notifications_pkey" PRIMARY KEY ("notification_id");



ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_pkey" PRIMARY KEY ("student_result_item_id");



ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_result_course_key" UNIQUE ("student_result_id", "course_id");



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_pkey" PRIMARY KEY ("student_result_id");



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_student_sem_ay_prog_key" UNIQUE ("student_id", "academic_year_id", "semester_id", "program_id");



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_email_key" UNIQUE ("institution_id", "email");



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_register_number_key" UNIQUE ("institution_id", "register_number");



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_student_number_key" UNIQUE ("institution_id", "student_number");



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_university_roll_number_key" UNIQUE ("institution_id", "university_roll_number");



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_pkey" PRIMARY KEY ("student_id");



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_user_id_key" UNIQUE ("user_id");



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_pkey" PRIMARY KEY ("test_result_id");



ALTER TABLE ONLY "public"."test_types"
    ADD CONSTRAINT "test_types_pkey" PRIMARY KEY ("code");



ALTER TABLE ONLY "public"."user_permission_grants"
    ADD CONSTRAINT "user_permission_grants_pkey" PRIMARY KEY ("grant_id");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_pkey" PRIMARY KEY ("user_id", "role_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_auth_user_id_key" UNIQUE ("auth_user_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



CREATE UNIQUE INDEX "academic_courses_normalized_code" ON "public"."courses" USING "btree" ("department_id", "lower"("btrim"("code")));



CREATE UNIQUE INDEX "academic_departments_normalized_code" ON "public"."departments" USING "btree" ("institution_id", "lower"("btrim"("code")));



CREATE UNIQUE INDEX "academic_programs_normalized_code" ON "public"."programs" USING "btree" ("department_id", "lower"("btrim"("code")));



CREATE UNIQUE INDEX "academic_sections_normalized_code" ON "public"."sections" USING "btree" ("course_offering_id", "lower"("btrim"("code")));



CREATE UNIQUE INDEX "academic_semesters_normalized_code" ON "public"."semesters" USING "btree" ("academic_year_id", "lower"("btrim"("code")));



CREATE UNIQUE INDEX "academic_years_normalized_code" ON "public"."academic_years" USING "btree" ("institution_id", "lower"("btrim"("code")));



CREATE UNIQUE INDEX "academic_years_one_current_per_institution_idx" ON "public"."academic_years" USING "btree" ("institution_id") WHERE ("is_current" = true);



CREATE INDEX "chunk_embeddings_embedding_hnsw_idx" ON "public"."chunk_embeddings" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops");



CREATE INDEX "course_offerings_program_id_idx" ON "public"."course_offerings" USING "btree" ("program_id");



CREATE INDEX "email_delivery_attempts_outbox_idx" ON "public"."email_delivery_attempts" USING "btree" ("outbox_id", "attempt_number" DESC);



CREATE INDEX "email_delivery_events_message_idx" ON "public"."email_delivery_events" USING "btree" ("provider_name", "provider_message_id");



CREATE INDEX "email_delivery_events_outbox_idx" ON "public"."email_delivery_events" USING "btree" ("outbox_id", "event_timestamp" DESC);



CREATE INDEX "email_outbox_aggregate_idx" ON "public"."email_outbox" USING "btree" ("aggregate_id", "created_at" DESC);



CREATE INDEX "email_outbox_claim_idx" ON "public"."email_outbox" USING "btree" ("available_at", "created_at") WHERE ("status" = 'pending'::"text");



CREATE UNIQUE INDEX "email_outbox_delivery_sequence_idx" ON "public"."email_outbox" USING "btree" ("delivery_sequence");



CREATE UNIQUE INDEX "email_outbox_provider_message_idx" ON "public"."email_outbox" USING "btree" ("provider_name", "provider_message_id") WHERE ("provider_message_id" IS NOT NULL);



CREATE INDEX "email_outbox_stale_lock_idx" ON "public"."email_outbox" USING "btree" ("locked_at") WHERE ("status" = 'processing'::"text");



CREATE INDEX "faculty_responsibilities_user_tenant" ON "public"."faculty_responsibilities" USING "btree" ("faculty_user_id", "institution_id");



CREATE UNIQUE INDEX "faculty_tests_duplicate" ON "public"."faculty_tests" USING "btree" ("section_id", "lower"("btrim"("title")), "scheduled_date") NULLS NOT DISTINCT WHERE ("status" <> 'CANCELLED'::"text");



CREATE INDEX "faculty_tests_scope" ON "public"."faculty_tests" USING "btree" ("institution_id", "section_id", "scheduled_date");



CREATE INDEX "idx_admin_audit_log_action" ON "public"."admin_audit_log" USING "btree" ("action");



CREATE INDEX "idx_admin_audit_log_actor_user_id" ON "public"."admin_audit_log" USING "btree" ("actor_user_id");



CREATE INDEX "idx_admin_audit_log_institution_time" ON "public"."admin_audit_log" USING "btree" ("institution_id", "performed_at" DESC);



CREATE INDEX "idx_admin_audit_log_performed_at" ON "public"."admin_audit_log" USING "btree" ("performed_at");



CREATE INDEX "idx_admin_audit_log_status" ON "public"."admin_audit_log" USING "btree" ("status");



CREATE INDEX "idx_auth_security_events_auth_user_time" ON "public"."auth_security_events" USING "btree" ("auth_user_id", "occurred_at" DESC);



CREATE INDEX "idx_auth_security_events_user_time" ON "public"."auth_security_events" USING "btree" ("user_id", "occurred_at" DESC);



CREATE INDEX "idx_conversations_user_id" ON "public"."conversations" USING "btree" ("user_id");



CREATE INDEX "idx_document_processing_runs_document_version_id" ON "public"."document_processing_runs" USING "btree" ("document_version_id");



CREATE INDEX "idx_document_versions_document_id" ON "public"."document_versions" USING "btree" ("document_id");



CREATE INDEX "idx_document_versions_supersedes_version_id" ON "public"."document_versions" USING "btree" ("supersedes_version_id");



CREATE INDEX "idx_documents_knowledge_source_id" ON "public"."documents" USING "btree" ("knowledge_source_id");



CREATE INDEX "idx_faculty_attendance_imports_section" ON "public"."faculty_attendance_imports" USING "btree" ("section_id", "created_at" DESC);



CREATE INDEX "idx_faculty_attendance_records_roster" ON "public"."faculty_attendance_records" USING "btree" ("roster_id");



CREATE INDEX "idx_faculty_attendance_rosters_identity" ON "public"."faculty_attendance_rosters" USING "btree" ("institution_id", "register_number", "university_roll_number");



CREATE INDEX "idx_faculty_attendance_rosters_linked_student" ON "public"."faculty_attendance_rosters" USING "btree" ("linked_student_id") WHERE ("linked_student_id" IS NOT NULL);



CREATE INDEX "idx_faculty_attendance_rosters_section" ON "public"."faculty_attendance_rosters" USING "btree" ("section_id", "roster_status");



CREATE INDEX "idx_faculty_attendance_sessions_section_date" ON "public"."faculty_attendance_sessions" USING "btree" ("section_id", "session_date" DESC);



CREATE INDEX "idx_faculty_section_assignments_faculty" ON "public"."faculty_section_assignments" USING "btree" ("faculty_user_id", "institution_id") WHERE ("revoked_at" IS NULL);



CREATE INDEX "idx_faculty_section_assignments_institution_section" ON "public"."faculty_section_assignments" USING "btree" ("institution_id", "section_id") WHERE ("revoked_at" IS NULL);



CREATE INDEX "idx_faqs_category" ON "public"."faqs" USING "btree" ("category");



CREATE INDEX "idx_faqs_institution_id" ON "public"."faqs" USING "btree" ("institution_id");



CREATE INDEX "idx_faqs_is_active" ON "public"."faqs" USING "btree" ("is_active");



CREATE INDEX "idx_faqs_is_published" ON "public"."faqs" USING "btree" ("is_published");



CREATE INDEX "idx_institution_join_requests_organization_status" ON "public"."institution_join_requests" USING "btree" ("organization_id", "status");



CREATE INDEX "idx_institution_join_requests_requested_by" ON "public"."institution_join_requests" USING "btree" ("requested_by_user_id");



CREATE INDEX "idx_institution_join_requests_status" ON "public"."institution_join_requests" USING "btree" ("status");



CREATE INDEX "idx_institution_membership_requests_inst_status" ON "public"."institution_membership_requests" USING "btree" ("institution_id", "status");



CREATE INDEX "idx_institution_membership_requests_org_status" ON "public"."institution_membership_requests" USING "btree" ("organization_id", "status");



CREATE INDEX "idx_institution_membership_requests_user_id" ON "public"."institution_membership_requests" USING "btree" ("user_id");



CREATE INDEX "idx_institutions_organization_id" ON "public"."institutions" USING "btree" ("organization_id");



CREATE INDEX "idx_institutions_organization_status" ON "public"."institutions" USING "btree" ("organization_id", "status");



CREATE INDEX "idx_institutions_status" ON "public"."institutions" USING "btree" ("status");



CREATE INDEX "idx_knowledge_chunks_processing_run_id" ON "public"."knowledge_chunks" USING "btree" ("processing_run_id");



CREATE INDEX "idx_knowledge_sources_created_by_user_id" ON "public"."knowledge_sources" USING "btree" ("created_by_user_id");



CREATE INDEX "idx_knowledge_sources_institution_id" ON "public"."knowledge_sources" USING "btree" ("institution_id");



CREATE INDEX "idx_knowledge_sources_owner_user_id" ON "public"."knowledge_sources" USING "btree" ("owner_user_id");



CREATE INDEX "idx_knowledge_sources_public_policy" ON "public"."knowledge_sources" USING "btree" ("institution_id", "visibility", "lifecycle_status");



CREATE INDEX "idx_message_citations_message_id" ON "public"."message_citations" USING "btree" ("message_id");



CREATE INDEX "idx_message_citations_retrieval_operation_id" ON "public"."message_citations" USING "btree" ("retrieval_operation_id");



CREATE INDEX "idx_notices_category" ON "public"."notices" USING "btree" ("category");



CREATE INDEX "idx_notices_institution_id" ON "public"."notices" USING "btree" ("institution_id");



CREATE INDEX "idx_notices_is_active" ON "public"."notices" USING "btree" ("is_active");



CREATE INDEX "idx_notices_is_pinned" ON "public"."notices" USING "btree" ("is_pinned");



CREATE INDEX "idx_notices_is_published" ON "public"."notices" USING "btree" ("is_published");



CREATE INDEX "idx_notices_priority" ON "public"."notices" USING "btree" ("priority");



CREATE INDEX "idx_notices_published_at" ON "public"."notices" USING "btree" ("published_at");



CREATE INDEX "idx_organizations_name" ON "public"."organizations" USING "btree" ("name");



CREATE INDEX "idx_organizations_status" ON "public"."organizations" USING "btree" ("status");



CREATE INDEX "idx_platform_institution_audit_action_time" ON "public"."platform_institution_audit_log" USING "btree" ("action", "performed_at" DESC);



CREATE INDEX "idx_platform_institution_audit_target_time" ON "public"."platform_institution_audit_log" USING "btree" ("institution_id", "performed_at" DESC);



CREATE INDEX "idx_platform_institution_audit_time" ON "public"."platform_institution_audit_log" USING "btree" ("performed_at" DESC);



CREATE INDEX "idx_platform_role_audit_target_time" ON "public"."platform_role_audit_log" USING "btree" ("target_user_id", "performed_at" DESC);



CREATE INDEX "idx_retrieval_operations_ai_response_id" ON "public"."retrieval_operations" USING "btree" ("ai_response_id");



CREATE INDEX "idx_retrieved_chunks_chunk_id" ON "public"."retrieved_chunks" USING "btree" ("chunk_id");



CREATE INDEX "idx_student_attendance_ay_semester" ON "public"."student_attendance" USING "btree" ("academic_year_id", "semester_id");



CREATE INDEX "idx_student_attendance_date" ON "public"."student_attendance" USING "btree" ("date");



CREATE INDEX "idx_student_attendance_institution_id" ON "public"."student_attendance" USING "btree" ("institution_id");



CREATE INDEX "idx_student_attendance_section_id" ON "public"."student_attendance" USING "btree" ("section_id");



CREATE INDEX "idx_student_attendance_student_date" ON "public"."student_attendance" USING "btree" ("student_id", "date");



CREATE INDEX "idx_student_attendance_student_id" ON "public"."student_attendance" USING "btree" ("student_id");



CREATE INDEX "idx_student_notifications_institution" ON "public"."student_notifications" USING "btree" ("institution_id");



CREATE INDEX "idx_student_notifications_read" ON "public"."student_notifications" USING "btree" ("student_id", "is_read") WHERE (NOT "is_read");



CREATE INDEX "idx_student_notifications_student" ON "public"."student_notifications" USING "btree" ("student_id", "created_at" DESC);



CREATE INDEX "idx_student_result_items_course_id" ON "public"."student_result_items" USING "btree" ("course_id");



CREATE INDEX "idx_student_result_items_result_id" ON "public"."student_result_items" USING "btree" ("student_result_id");



CREATE INDEX "idx_student_result_items_section_id" ON "public"."student_result_items" USING "btree" ("section_id");



CREATE INDEX "idx_student_results_ay_semester" ON "public"."student_results" USING "btree" ("academic_year_id", "semester_id");



CREATE INDEX "idx_student_results_institution_id" ON "public"."student_results" USING "btree" ("institution_id");



CREATE INDEX "idx_student_results_program_id" ON "public"."student_results" USING "btree" ("program_id");



CREATE INDEX "idx_student_results_student_id" ON "public"."student_results" USING "btree" ("student_id");



CREATE INDEX "idx_student_results_student_issued" ON "public"."student_results" USING "btree" ("student_id", "issued_at");



CREATE INDEX "idx_students_academic_year_id" ON "public"."students" USING "btree" ("academic_year_id");



CREATE INDEX "idx_students_email" ON "public"."students" USING "btree" ("email");



CREATE INDEX "idx_students_institution_approval" ON "public"."students" USING "btree" ("institution_id", "approval_status");



CREATE INDEX "idx_students_institution_id" ON "public"."students" USING "btree" ("institution_id");



CREATE INDEX "idx_students_is_active" ON "public"."students" USING "btree" ("is_active");



CREATE INDEX "idx_students_program_id" ON "public"."students" USING "btree" ("program_id");



CREATE INDEX "idx_students_register_number" ON "public"."students" USING "btree" ("register_number");



CREATE INDEX "idx_students_university_roll_number" ON "public"."students" USING "btree" ("university_roll_number");



CREATE INDEX "idx_students_user_id" ON "public"."students" USING "btree" ("user_id");



CREATE INDEX "idx_test_results_ay_semester" ON "public"."test_results" USING "btree" ("academic_year_id", "semester_id");



CREATE INDEX "idx_test_results_course_id" ON "public"."test_results" USING "btree" ("course_id");



CREATE INDEX "idx_test_results_institution_id" ON "public"."test_results" USING "btree" ("institution_id");



CREATE INDEX "idx_test_results_section_id" ON "public"."test_results" USING "btree" ("section_id");



CREATE INDEX "idx_test_results_student_conducted" ON "public"."test_results" USING "btree" ("student_id", "conducted_at");



CREATE INDEX "idx_test_results_student_id" ON "public"."test_results" USING "btree" ("student_id");



CREATE INDEX "idx_user_permission_grants_user_institution" ON "public"."user_permission_grants" USING "btree" ("user_id", "institution_id") WHERE ("revoked_at" IS NULL);



CREATE INDEX "idx_user_roles_scope_organization" ON "public"."user_roles" USING "btree" ("scope_organization_id");



CREATE INDEX "idx_user_roles_scope_type_scope_id" ON "public"."user_roles" USING "btree" ("scope_type", "scope_id");



CREATE INDEX "idx_user_roles_user_scope" ON "public"."user_roles" USING "btree" ("user_id", "scope_type");



CREATE UNIQUE INDEX "institutions_code_upper_key" ON "public"."institutions" USING "btree" ("upper"("code"));



CREATE INDEX "platform_admin_invitations_delivery_status_idx" ON "public"."platform_admin_invitations" USING "btree" ("email_delivery_status") WHERE ("status" = 'invited'::"text");



CREATE INDEX "platform_admin_invitations_email_idx" ON "public"."platform_admin_invitations" USING "btree" ("email");



CREATE INDEX "platform_admin_invitations_institution_status_idx" ON "public"."platform_admin_invitations" USING "btree" ("institution_id", "status");



CREATE UNIQUE INDEX "platform_admin_invitations_one_pending_email_idx" ON "public"."platform_admin_invitations" USING "btree" ("institution_id", "lower"("email")) WHERE ("status" = 'invited'::"text");



CREATE INDEX "platform_admin_invitations_status_expiry_idx" ON "public"."platform_admin_invitations" USING "btree" ("status", "expires_at");



CREATE INDEX "program_courses_course_id_idx" ON "public"."program_courses" USING "btree" ("course_id");



CREATE INDEX "role_permissions_permission_id_idx" ON "public"."role_permissions" USING "btree" ("permission_id");



CREATE UNIQUE INDEX "semesters_one_current_per_academic_year_idx" ON "public"."semesters" USING "btree" ("academic_year_id") WHERE ("is_current" = true);



CREATE UNIQUE INDEX "test_results_legacy_unique" ON "public"."test_results" USING "btree" ("student_id", "course_id", "test_name", "academic_year_id", "semester_id") WHERE ("test_id" IS NULL);



CREATE UNIQUE INDEX "test_results_test_roster" ON "public"."test_results" USING "btree" ("test_id", "roster_id") WHERE ("test_id" IS NOT NULL);



CREATE UNIQUE INDEX "test_results_test_student" ON "public"."test_results" USING "btree" ("test_id", "student_id") WHERE (("test_id" IS NOT NULL) AND ("student_id" IS NOT NULL));



CREATE UNIQUE INDEX "uq_faculty_section_assignments_active" ON "public"."faculty_section_assignments" USING "btree" ("faculty_user_id", "section_id") WHERE ("revoked_at" IS NULL);



CREATE UNIQUE INDEX "uq_institution_join_request_open" ON "public"."institution_join_requests" USING "btree" ("institution_id") WHERE ("status" = 'pending'::"text");



CREATE UNIQUE INDEX "uq_institution_membership_request_open" ON "public"."institution_membership_requests" USING "btree" ("user_id", "requested_role") WHERE ("status" = 'pending'::"text");



CREATE UNIQUE INDEX "uq_organizations_code_lower" ON "public"."organizations" USING "btree" ("lower"("organization_code"));



CREATE UNIQUE INDEX "uq_platform_super_admin_invitations_pending_email" ON "public"."platform_super_admin_invitations" USING "btree" ("email") WHERE ("status" = 'invited'::"text");



CREATE UNIQUE INDEX "uq_student_notification_source_record" ON "public"."student_notifications" USING "btree" ("student_id", "source_record_id", "notification_type") WHERE ("source_record_id" IS NOT NULL);



CREATE UNIQUE INDEX "uq_user_permission_grants_active" ON "public"."user_permission_grants" USING "btree" ("user_id", "institution_id", "permission_id") WHERE ("revoked_at" IS NULL);



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."academic_years" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."course_offerings" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."courses" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."departments" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."program_courses" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."programs" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."sections" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "academic_master_validate" BEFORE INSERT OR UPDATE ON "public"."semesters" FOR EACH ROW EXECUTE FUNCTION "public"."validate_academic_master_record"();



CREATE OR REPLACE TRIGGER "faculty_assignment_touch" BEFORE UPDATE ON "public"."faculty_section_assignments" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_assignment_touch"();



CREATE OR REPLACE TRIGGER "faculty_responsibility_scope_guard" BEFORE INSERT OR UPDATE ON "public"."faculty_responsibilities" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_responsibility_scope_guard"();



CREATE OR REPLACE TRIGGER "faculty_test_context" BEFORE INSERT OR UPDATE ON "public"."faculty_tests" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_test_context_guard"();



CREATE OR REPLACE TRIGGER "guard_test_import" BEFORE INSERT OR DELETE OR UPDATE ON "public"."faculty_attendance_imports" FOR EACH ROW EXECUTE FUNCTION "public"."guard_test_import_workflow"();



CREATE OR REPLACE TRIGGER "guard_test_import_rows" BEFORE INSERT OR DELETE OR UPDATE ON "public"."faculty_attendance_import_rows" FOR EACH ROW EXECUTE FUNCTION "public"."guard_test_import_workflow"();



CREATE OR REPLACE TRIGGER "phase81_admin_audit_append_only" BEFORE DELETE OR UPDATE ON "public"."admin_audit_log" FOR EACH ROW EXECUTE FUNCTION "public"."phase81_prevent_audit_mutation"();



CREATE OR REPLACE TRIGGER "reconcile_faculty_test_roster" AFTER UPDATE OF "linked_student_id", "reconciliation_state", "roster_status" ON "public"."faculty_attendance_rosters" FOR EACH ROW EXECUTE FUNCTION "public"."reconcile_faculty_test_roster"();



CREATE OR REPLACE TRIGGER "test_student_visibility" AFTER UPDATE OF "approval_status", "is_active", "status", "program_id", "academic_year_id" ON "public"."students" FOR EACH ROW EXECUTE FUNCTION "public"."refresh_student_test_visibility"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_import_context" BEFORE INSERT OR UPDATE ON "public"."faculty_attendance_imports" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_context_guard"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_imports_updated_at" BEFORE UPDATE ON "public"."faculty_attendance_imports" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_record_scope" BEFORE INSERT OR UPDATE ON "public"."faculty_attendance_records" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_record_scope_guard"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_records_updated_at" BEFORE UPDATE ON "public"."faculty_attendance_records" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_roster_context" BEFORE INSERT OR UPDATE ON "public"."faculty_attendance_rosters" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_context_guard"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_rosters_updated_at" BEFORE UPDATE ON "public"."faculty_attendance_rosters" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_faculty_attendance_session_context" BEFORE INSERT OR UPDATE ON "public"."faculty_attendance_sessions" FOR EACH ROW EXECUTE FUNCTION "public"."faculty_attendance_context_guard"();



CREATE OR REPLACE TRIGGER "trg_phase613_institutions_status" BEFORE INSERT OR UPDATE ON "public"."institutions" FOR EACH ROW EXECUTE FUNCTION "public"."phase613_sync_institution_status"();



CREATE OR REPLACE TRIGGER "trg_phase613_join_request_organization" BEFORE INSERT OR UPDATE ON "public"."institution_join_requests" FOR EACH ROW EXECUTE FUNCTION "public"."phase613_assert_child_organization"();



CREATE OR REPLACE TRIGGER "trg_phase613_membership_request_organization" BEFORE INSERT OR UPDATE ON "public"."institution_membership_requests" FOR EACH ROW EXECUTE FUNCTION "public"."phase613_assert_child_organization"();



CREATE OR REPLACE TRIGGER "trg_phase613_user_roles_scope" BEFORE INSERT OR UPDATE OF "scope_type", "scope_id", "scope_organization_id" ON "public"."user_roles" FOR EACH ROW EXECUTE FUNCTION "public"."phase613_assert_role_scope"();



CREATE OR REPLACE TRIGGER "trg_phase712_super_admin_scope" BEFORE INSERT OR UPDATE OF "role_id", "scope_type", "scope_id", "scope_organization_id" ON "public"."user_roles" FOR EACH ROW EXECUTE FUNCTION "public"."phase712_assert_super_admin_scope"();



CREATE OR REPLACE TRIGGER "trg_phase715_invitation_transition" BEFORE UPDATE ON "public"."platform_admin_invitations" FOR EACH ROW EXECUTE FUNCTION "public"."phase715_assert_invitation_transition"();



CREATE OR REPLACE TRIGGER "trg_phase717_cancel_terminal_invitation_email" AFTER UPDATE OF "status" ON "public"."platform_admin_invitations" FOR EACH ROW EXECUTE FUNCTION "public"."phase717_cancel_terminal_invitation_email"();



CREATE OR REPLACE TRIGGER "trg_reconcile_faculty_attendance_roster" AFTER INSERT OR UPDATE OF "register_number", "university_roll_number", "approval_status", "status", "is_active" ON "public"."students" FOR EACH ROW EXECUTE FUNCTION "public"."reconcile_faculty_attendance_roster_student"();



CREATE OR REPLACE TRIGGER "trg_student_attendance_tenant_guard" BEFORE INSERT OR UPDATE ON "public"."student_attendance" FOR EACH ROW EXECUTE FUNCTION "public"."student_attendance_tenant_guard"();



CREATE OR REPLACE TRIGGER "trg_student_notifications_tenant_guard" BEFORE INSERT OR UPDATE ON "public"."student_notifications" FOR EACH ROW EXECUTE FUNCTION "public"."trg_student_notifications_tenant_guard"();



CREATE OR REPLACE TRIGGER "trg_student_results_tenant_guard" BEFORE INSERT OR UPDATE ON "public"."student_results" FOR EACH ROW EXECUTE FUNCTION "public"."student_results_tenant_guard"();



CREATE OR REPLACE TRIGGER "trg_test_results_tenant_guard" BEFORE INSERT OR UPDATE ON "public"."test_results" FOR EACH ROW EXECUTE FUNCTION "public"."test_results_tenant_guard"();



CREATE OR REPLACE TRIGGER "workflow_result_delete" BEFORE DELETE ON "public"."test_results" FOR EACH ROW EXECUTE FUNCTION "public"."guard_workflow_result_delete"();



ALTER TABLE ONLY "public"."academic_years"
    ADD CONSTRAINT "academic_years_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."admin_audit_log"
    ADD CONSTRAINT "admin_audit_log_actor_user_id_fkey" FOREIGN KEY ("actor_user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."admin_audit_log"
    ADD CONSTRAINT "admin_audit_log_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."ai_responses"
    ADD CONSTRAINT "ai_responses_message_id_fkey" FOREIGN KEY ("message_id") REFERENCES "public"."messages"("message_id");



ALTER TABLE ONLY "public"."auth_security_events"
    ADD CONSTRAINT "auth_security_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."campuses"
    ADD CONSTRAINT "campuses_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."chunk_embeddings"
    ADD CONSTRAINT "chunk_embeddings_chunk_id_fkey" FOREIGN KEY ("chunk_id") REFERENCES "public"."knowledge_chunks"("chunk_id") ON DELETE CASCADE;



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



ALTER TABLE ONLY "public"."email_delivery_attempts"
    ADD CONSTRAINT "email_delivery_attempts_outbox_fkey" FOREIGN KEY ("outbox_id") REFERENCES "public"."email_outbox"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."email_delivery_events"
    ADD CONSTRAINT "email_delivery_events_outbox_fkey" FOREIGN KEY ("outbox_id") REFERENCES "public"."email_outbox"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."email_outbox"
    ADD CONSTRAINT "email_outbox_invitation_fkey" FOREIGN KEY ("aggregate_id") REFERENCES "public"."platform_admin_invitations"("invitation_id");



ALTER TABLE ONLY "public"."faculty_attendance_import_rows"
    ADD CONSTRAINT "faculty_attendance_import_rows_import_id_fkey" FOREIGN KEY ("import_id") REFERENCES "public"."faculty_attendance_imports"("import_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_course_offering_id_fkey" FOREIGN KEY ("course_offering_id") REFERENCES "public"."course_offerings"("course_offering_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_test_id_fkey" FOREIGN KEY ("test_id") REFERENCES "public"."faculty_tests"("test_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_imports"
    ADD CONSTRAINT "faculty_attendance_imports_uploaded_by_fkey" FOREIGN KEY ("uploaded_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_records"
    ADD CONSTRAINT "faculty_attendance_records_roster_id_fkey" FOREIGN KEY ("roster_id") REFERENCES "public"."faculty_attendance_rosters"("roster_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."faculty_attendance_records"
    ADD CONSTRAINT "faculty_attendance_records_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."faculty_attendance_sessions"("session_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_course_offering_id_fkey" FOREIGN KEY ("course_offering_id") REFERENCES "public"."course_offerings"("course_offering_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_linked_student_id_fkey" FOREIGN KEY ("linked_student_id") REFERENCES "public"."students"("student_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_rosters"
    ADD CONSTRAINT "faculty_attendance_rosters_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_sessions"
    ADD CONSTRAINT "faculty_attendance_sessions_conducted_by_fkey" FOREIGN KEY ("conducted_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_sessions"
    ADD CONSTRAINT "faculty_attendance_sessions_course_offering_id_fkey" FOREIGN KEY ("course_offering_id") REFERENCES "public"."course_offerings"("course_offering_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_sessions"
    ADD CONSTRAINT "faculty_attendance_sessions_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_attendance_sessions"
    ADD CONSTRAINT "faculty_attendance_sessions_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."departments"("department_id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_faculty_user_id_fkey" FOREIGN KEY ("faculty_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_responsibility_code_fkey" FOREIGN KEY ("responsibility_code") REFERENCES "public"."responsibility_definitions"("code");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_revoked_by_fkey" FOREIGN KEY ("revoked_by") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id");



ALTER TABLE ONLY "public"."faculty_responsibilities"
    ADD CONSTRAINT "faculty_responsibilities_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id");



ALTER TABLE ONLY "public"."faculty_section_assignments"
    ADD CONSTRAINT "faculty_section_assignments_assigned_by_fkey" FOREIGN KEY ("assigned_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_section_assignments"
    ADD CONSTRAINT "faculty_section_assignments_faculty_user_id_fkey" FOREIGN KEY ("faculty_user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_section_assignments"
    ADD CONSTRAINT "faculty_section_assignments_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_section_assignments"
    ADD CONSTRAINT "faculty_section_assignments_revoked_by_fkey" FOREIGN KEY ("revoked_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_section_assignments"
    ADD CONSTRAINT "faculty_section_assignments_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_tests"
    ADD CONSTRAINT "faculty_tests_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."faculty_tests"
    ADD CONSTRAINT "faculty_tests_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_tests"
    ADD CONSTRAINT "faculty_tests_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."faculty_tests"
    ADD CONSTRAINT "faculty_tests_test_type_fkey" FOREIGN KEY ("test_type") REFERENCES "public"."test_types"("code");



ALTER TABLE ONLY "public"."faculty_tests"
    ADD CONSTRAINT "faculty_tests_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."faqs"
    ADD CONSTRAINT "faqs_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_decided_by_fkey" FOREIGN KEY ("decided_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("organization_id");



ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_requested_by_fkey" FOREIGN KEY ("requested_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_decided_by_fkey" FOREIGN KEY ("decided_by_user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("organization_id");



ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."institutions"
    ADD CONSTRAINT "institutions_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("organization_id");



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



ALTER TABLE ONLY "public"."notices"
    ADD CONSTRAINT "notices_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."notices"
    ADD CONSTRAINT "notices_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_accepted_user_id_fkey" FOREIGN KEY ("accepted_user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_log_actor_user_id_fkey" FOREIGN KEY ("actor_user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_log_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_log_target_user_id_fkey" FOREIGN KEY ("target_user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_role_audit_log"
    ADD CONSTRAINT "platform_role_audit_log_target_fkey" FOREIGN KEY ("target_user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."platform_super_admin_invitations"
    ADD CONSTRAINT "platform_super_admin_invitations_accepted_user_fkey" FOREIGN KEY ("accepted_user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."platform_super_admin_invitations"
    ADD CONSTRAINT "platform_super_admin_invitations_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id");



ALTER TABLE ONLY "public"."program_courses"
    ADD CONSTRAINT "program_courses_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id");



ALTER TABLE ONLY "public"."programs"
    ADD CONSTRAINT "programs_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."departments"("department_id");



ALTER TABLE ONLY "public"."responsibility_permissions"
    ADD CONSTRAINT "responsibility_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "public"."permissions"("permission_id");



ALTER TABLE ONLY "public"."responsibility_permissions"
    ADD CONSTRAINT "responsibility_permissions_responsibility_code_fkey" FOREIGN KEY ("responsibility_code") REFERENCES "public"."responsibility_definitions"("code");



ALTER TABLE ONLY "public"."retrieval_operations"
    ADD CONSTRAINT "retrieval_operations_ai_response_id_fkey" FOREIGN KEY ("ai_response_id") REFERENCES "public"."ai_responses"("ai_response_id");



ALTER TABLE ONLY "public"."retrieved_chunks"
    ADD CONSTRAINT "retrieved_chunks_chunk_id_fkey" FOREIGN KEY ("chunk_id") REFERENCES "public"."knowledge_chunks"("chunk_id");



ALTER TABLE ONLY "public"."retrieved_chunks"
    ADD CONSTRAINT "retrieved_chunks_retrieval_operation_id_fkey" FOREIGN KEY ("retrieval_operation_id") REFERENCES "public"."retrieval_operations"("retrieval_operation_id");



ALTER TABLE ONLY "public"."role_permissions"
    ADD CONSTRAINT "role_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "public"."permissions"("permission_id");



ALTER TABLE ONLY "public"."role_permissions"
    ADD CONSTRAINT "role_permissions_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id");



ALTER TABLE ONLY "public"."sections"
    ADD CONSTRAINT "sections_course_offering_id_fkey" FOREIGN KEY ("course_offering_id") REFERENCES "public"."course_offerings"("course_offering_id");



ALTER TABLE ONLY "public"."semesters"
    ADD CONSTRAINT "semesters_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id");



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_attendance"
    ADD CONSTRAINT "student_attendance_student_id_fkey" FOREIGN KEY ("student_id") REFERENCES "public"."students"("student_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."student_notifications"
    ADD CONSTRAINT "student_notifications_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."student_notifications"
    ADD CONSTRAINT "student_notifications_student_id_fkey" FOREIGN KEY ("student_id") REFERENCES "public"."students"("student_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."student_result_items"
    ADD CONSTRAINT "student_result_items_student_result_id_fkey" FOREIGN KEY ("student_result_id") REFERENCES "public"."student_results"("student_result_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_student_id_fkey" FOREIGN KEY ("student_id") REFERENCES "public"."students"("student_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_program_id_fkey" FOREIGN KEY ("program_id") REFERENCES "public"."programs"("program_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."students"
    ADD CONSTRAINT "students_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_academic_year_id_fkey" FOREIGN KEY ("academic_year_id") REFERENCES "public"."academic_years"("academic_year_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_course_id_fkey" FOREIGN KEY ("course_id") REFERENCES "public"."courses"("course_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id");



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_roster_id_fkey" FOREIGN KEY ("roster_id") REFERENCES "public"."faculty_attendance_rosters"("roster_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."sections"("section_id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_semester_id_fkey" FOREIGN KEY ("semester_id") REFERENCES "public"."semesters"("semester_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_student_id_fkey" FOREIGN KEY ("student_id") REFERENCES "public"."students"("student_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_test_id_fkey" FOREIGN KEY ("test_id") REFERENCES "public"."faculty_tests"("test_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_test_type_fkey" FOREIGN KEY ("test_type") REFERENCES "public"."test_types"("code");



ALTER TABLE ONLY "public"."user_permission_grants"
    ADD CONSTRAINT "user_permission_grants_granted_by_fkey" FOREIGN KEY ("granted_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."user_permission_grants"
    ADD CONSTRAINT "user_permission_grants_institution_id_fkey" FOREIGN KEY ("institution_id") REFERENCES "public"."institutions"("institution_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."user_permission_grants"
    ADD CONSTRAINT "user_permission_grants_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "public"."permissions"("permission_id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."user_permission_grants"
    ADD CONSTRAINT "user_permission_grants_revoked_by_fkey" FOREIGN KEY ("revoked_by") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."user_permission_grants"
    ADD CONSTRAINT "user_permission_grants_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id");



ALTER TABLE ONLY "public"."user_roles"
    ADD CONSTRAINT "user_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_auth_user_id_fkey" FOREIGN KEY ("auth_user_id") REFERENCES "auth"."users"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE "public"."academic_years" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."auth_consumed_password_recovery_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."auth_security_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."course_offerings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."courses" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."departments" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."email_delivery_attempts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."email_delivery_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."email_outbox" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_attendance_import_rows" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_attendance_imports" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_attendance_records" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_attendance_rosters" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_attendance_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_responsibilities" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_section_assignments" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."faculty_tests" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."platform_super_admin_invitations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."program_courses" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."programs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."responsibility_definitions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."responsibility_permissions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."sections" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."semesters" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."test_results" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."test_types" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_permission_grants" ENABLE ROW LEVEL SECURITY;


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



REVOKE ALL ON FUNCTION "public"."academic_master_tenant"("p_entity" "text", "p_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."academic_master_tenant"("p_entity" "text", "p_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."assert_faculty_academic_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_permission" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."assert_faculty_academic_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_permission" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."assert_faculty_attendance_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."assert_faculty_attendance_mutation"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid") TO "service_role";



GRANT ALL ON TABLE "public"."faculty_tests" TO "service_role";



REVOKE ALL ON FUNCTION "public"."assert_test_version"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."assert_test_version"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint) TO "service_role";



REVOKE ALL ON FUNCTION "public"."commit_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_expected_updated_at" timestamp with time zone, "p_rows" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."commit_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_expected_updated_at" timestamp with time zone, "p_rows" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."commit_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_version" bigint) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."commit_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_version" bigint) TO "service_role";



REVOKE ALL ON FUNCTION "public"."consume_auth_password_recovery_session"("p_session_fingerprint" "text", "p_auth_user_id" "uuid", "p_expires_at" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."consume_auth_password_recovery_session"("p_session_fingerprint" "text", "p_auth_user_id" "uuid", "p_expires_at" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."create_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."create_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."faculty_assignment_touch"() TO "anon";
GRANT ALL ON FUNCTION "public"."faculty_assignment_touch"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."faculty_assignment_touch"() TO "service_role";



GRANT ALL ON FUNCTION "public"."faculty_attendance_context_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."faculty_attendance_context_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."faculty_attendance_context_guard"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."faculty_attendance_identity"("p_tenant" "uuid", "p_register" "text", "p_roll" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."faculty_attendance_identity"("p_tenant" "uuid", "p_register" "text", "p_roll" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."faculty_attendance_record_scope_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."faculty_attendance_record_scope_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."faculty_attendance_record_scope_guard"() TO "service_role";



GRANT ALL ON FUNCTION "public"."faculty_attendance_set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."faculty_attendance_set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."faculty_attendance_set_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."faculty_responsibility_scope_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."faculty_responsibility_scope_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."faculty_responsibility_scope_guard"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."faculty_test_context_guard"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."faculty_test_context_guard"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."guard_test_import_workflow"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_test_import_workflow"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."guard_workflow_result_delete"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_workflow_result_delete"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."manage_academic_master_record"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_entity" "text", "p_record_id" "uuid", "p_payload" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."manage_academic_master_record"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_entity" "text", "p_record_id" "uuid", "p_payload" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."manage_faculty_responsibility"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_responsibility_code" "text", "p_scope_type" "text", "p_scope_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_responsibility_id" "uuid", "p_revoke" boolean, "p_program_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."manage_faculty_responsibility"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_responsibility_code" "text", "p_scope_type" "text", "p_scope_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_responsibility_id" "uuid", "p_revoke" boolean, "p_program_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."manage_scoped_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_revoke" boolean) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."manage_scoped_faculty_teaching_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean, "p_revoke" boolean) TO "service_role";



REVOKE ALL ON FUNCTION "public"."mark_faculty_attendance"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_session_date" "date", "p_attendance" "jsonb", "p_notes" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."mark_faculty_attendance"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_session_date" "date", "p_attendance" "jsonb", "p_notes" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."phase613_assert_child_organization"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase613_assert_child_organization"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase613_assert_child_organization"() TO "service_role";



GRANT ALL ON FUNCTION "public"."phase613_assert_role_scope"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase613_assert_role_scope"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase613_assert_role_scope"() TO "service_role";



GRANT ALL ON FUNCTION "public"."phase613_sync_institution_status"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase613_sync_institution_status"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase613_sync_institution_status"() TO "service_role";



GRANT ALL ON FUNCTION "public"."phase712_assert_super_admin_scope"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase712_assert_super_admin_scope"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase712_assert_super_admin_scope"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase712_assign_super_admin"("p_target_email" "text", "p_actor_identifier" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase712_assign_super_admin"("p_target_email" "text", "p_actor_identifier" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase712_revoke_super_admin"("p_target_email" "text", "p_actor_identifier" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase712_revoke_super_admin"("p_target_email" "text", "p_actor_identifier" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase714_assert_invitation_transition"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase714_assert_invitation_transition"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase714_assert_invitation_transition"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase714_assert_invitation_transition"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase715_assert_invitation_transition"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase715_assert_invitation_transition"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase715_assert_invitation_transition"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase715_assert_invitation_transition"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_cancel_terminal_invitation_email"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_cancel_terminal_invitation_email"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase717_cancel_terminal_invitation_email"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase717_cancel_terminal_invitation_email"() TO "service_role";



GRANT ALL ON TABLE "public"."email_outbox" TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_claim_email_outbox"("p_batch_size" integer, "p_lock_seconds" integer, "p_retry_limit" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_claim_email_outbox"("p_batch_size" integer, "p_lock_seconds" integer, "p_retry_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."phase717_claim_email_outbox"("p_batch_size" integer, "p_lock_seconds" integer, "p_retry_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase717_claim_email_outbox"("p_batch_size" integer, "p_lock_seconds" integer, "p_retry_limit" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_complete_email_outbox"("p_outbox_id" "uuid", "p_attempt_number" integer, "p_outcome" "text", "p_provider_name" "text", "p_provider_message_id" "text", "p_failure_category" "text", "p_available_at" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_complete_email_outbox"("p_outbox_id" "uuid", "p_attempt_number" integer, "p_outcome" "text", "p_provider_name" "text", "p_provider_message_id" "text", "p_failure_category" "text", "p_available_at" timestamp with time zone) TO "anon";
GRANT ALL ON FUNCTION "public"."phase717_complete_email_outbox"("p_outbox_id" "uuid", "p_attempt_number" integer, "p_outcome" "text", "p_provider_name" "text", "p_provider_message_id" "text", "p_failure_category" "text", "p_available_at" timestamp with time zone) TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase717_complete_email_outbox"("p_outbox_id" "uuid", "p_attempt_number" integer, "p_outcome" "text", "p_provider_name" "text", "p_provider_message_id" "text", "p_failure_category" "text", "p_available_at" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text", "p_role_name" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"("p_institution_id" "uuid", "p_email" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_created_by" "uuid", "p_protected_token" "text", "p_role_name" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_resolve_email_outbox_context"("p_outbox_id" "uuid", "p_token_hash" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_resolve_email_outbox_context"("p_outbox_id" "uuid", "p_token_hash" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."phase717_resolve_email_outbox_context"("p_outbox_id" "uuid", "p_token_hash" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase717_resolve_email_outbox_context"("p_outbox_id" "uuid", "p_token_hash" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase717_rotate_invitation_with_outbox"("p_invitation_id" "uuid", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_expected_updated_at" timestamp with time zone, "p_protected_token" "text", "p_lock_seconds" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase717_rotate_invitation_with_outbox"("p_invitation_id" "uuid", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_expected_updated_at" timestamp with time zone, "p_protected_token" "text", "p_lock_seconds" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."phase717_rotate_invitation_with_outbox"("p_invitation_id" "uuid", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_expected_updated_at" timestamp with time zone, "p_protected_token" "text", "p_lock_seconds" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase717_rotate_invitation_with_outbox"("p_invitation_id" "uuid", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_expected_updated_at" timestamp with time zone, "p_protected_token" "text", "p_lock_seconds" integer) TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase718_reconcile_mailgun_event"("p_event_key" "text", "p_replay_token_digest" "text", "p_provider_event_id" "text", "p_provider_message_id" "text", "p_event_type" "text", "p_event_timestamp" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase718_reconcile_mailgun_event"("p_event_key" "text", "p_replay_token_digest" "text", "p_provider_event_id" "text", "p_provider_message_id" "text", "p_event_type" "text", "p_event_timestamp" timestamp with time zone) TO "anon";
GRANT ALL ON FUNCTION "public"."phase718_reconcile_mailgun_event"("p_event_key" "text", "p_replay_token_digest" "text", "p_provider_event_id" "text", "p_provider_message_id" "text", "p_event_type" "text", "p_event_timestamp" timestamp with time zone) TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase718_reconcile_mailgun_event"("p_event_key" "text", "p_replay_token_digest" "text", "p_provider_event_id" "text", "p_provider_message_id" "text", "p_event_type" "text", "p_event_timestamp" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase723_approve_membership_and_grant_role"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase723_approve_membership_and_grant_role"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase723_approve_membership_with_invitation"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_protected_token" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase723_approve_membership_with_invitation"("p_request_id" "uuid", "p_institution_id" "uuid", "p_decided_by" "uuid", "p_reason" "text", "p_token_hash" "text", "p_expires_at" timestamp with time zone, "p_protected_token" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase81_assert_institution_admin"("p_actor_user_id" "uuid", "p_institution_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase81_assert_institution_admin"("p_actor_user_id" "uuid", "p_institution_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase81_assign_institution_role_audited"("p_actor_user_id" "uuid", "p_target_user_id" "uuid", "p_institution_id" "uuid", "p_role_name" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase81_assign_institution_role_audited"("p_actor_user_id" "uuid", "p_target_user_id" "uuid", "p_institution_id" "uuid", "p_role_name" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase81_manage_faculty_section_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase81_manage_faculty_section_assignment"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean) TO "service_role";



REVOKE ALL ON FUNCTION "public"."phase81_manage_faculty_section_assignment_original"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_faculty_user_id" "uuid", "p_section_id" "uuid", "p_revoke" boolean) FROM PUBLIC;



REVOKE ALL ON FUNCTION "public"."phase81_manage_staff_permission_grants"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_target_user_id" "uuid", "p_permission_codes" "text"[], "p_grant" boolean) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."phase81_manage_staff_permission_grants"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_target_user_id" "uuid", "p_permission_codes" "text"[], "p_grant" boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."phase81_prevent_audit_mutation"() TO "anon";
GRANT ALL ON FUNCTION "public"."phase81_prevent_audit_mutation"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."phase81_prevent_audit_mutation"() TO "service_role";



GRANT ALL ON FUNCTION "public"."reconcile_faculty_attendance_roster_student"() TO "anon";
GRANT ALL ON FUNCTION "public"."reconcile_faculty_attendance_roster_student"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."reconcile_faculty_attendance_roster_student"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."reconcile_faculty_test_roster"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reconcile_faculty_test_roster"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."refresh_student_test_visibility"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."refresh_student_test_visibility"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."review_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_summary" "jsonb", "p_rows" "jsonb", "p_expected_updated_at" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."review_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import_id" "uuid", "p_summary" "jsonb", "p_rows" "jsonb", "p_expected_updated_at" timestamp with time zone) TO "service_role";



REVOKE ALL ON FUNCTION "public"."review_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_summary" "jsonb", "p_rows" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."review_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_import" "uuid", "p_updated_at" timestamp with time zone, "p_summary" "jsonb", "p_rows" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."save_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_data" "jsonb", "p_test" "uuid", "p_version" bigint) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."save_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_section" "uuid", "p_data" "jsonb", "p_test" "uuid", "p_version" bigint) TO "service_role";



REVOKE ALL ON FUNCTION "public"."save_faculty_test_marks"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_rows" "jsonb", "p_reason" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."save_faculty_test_marks"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_rows" "jsonb", "p_reason" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."search_public_knowledge_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid", "filter_model_name" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."search_public_knowledge_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid", "filter_model_name" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."search_similar_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid", "filter_document_id" "uuid", "filter_document_version_id" "uuid", "filter_processing_run_id" "uuid", "filter_model_name" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."search_similar_chunks"("query_embedding" "extensions"."vector", "match_count" integer, "filter_institution_id" "uuid", "filter_knowledge_source_id" "uuid", "filter_document_id" "uuid", "filter_document_version_id" "uuid", "filter_processing_run_id" "uuid", "filter_model_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."stage_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_semester_id" "uuid", "p_filename" "text", "p_file_type" "text", "p_strategy" "text", "p_ai_confirmed" boolean, "p_summary" "jsonb", "p_rows" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."stage_faculty_attendance_import"("p_actor" "uuid", "p_tenant" "uuid", "p_section_id" "uuid", "p_semester_id" "uuid", "p_filename" "text", "p_file_type" "text", "p_strategy" "text", "p_ai_confirmed" boolean, "p_summary" "jsonb", "p_rows" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."stage_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_filename" "text", "p_strategy" "text", "p_summary" "jsonb", "p_rows" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."stage_faculty_test_import"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_filename" "text", "p_strategy" "text", "p_summary" "jsonb", "p_rows" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."student_attendance_tenant_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."student_attendance_tenant_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."student_attendance_tenant_guard"() TO "service_role";



GRANT ALL ON FUNCTION "public"."student_results_tenant_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."student_results_tenant_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."student_results_tenant_guard"() TO "service_role";



GRANT ALL ON FUNCTION "public"."test_results_tenant_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."test_results_tenant_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."test_results_tenant_guard"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."transition_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_action" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."transition_faculty_test"("p_actor" "uuid", "p_tenant" "uuid", "p_test" "uuid", "p_version" bigint, "p_action" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."trg_student_notifications_tenant_guard"() TO "anon";
GRANT ALL ON FUNCTION "public"."trg_student_notifications_tenant_guard"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."trg_student_notifications_tenant_guard"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_faculty_teaching_validity"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_faculty_teaching_validity"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_assignment_id" "uuid", "p_start_at" timestamp with time zone, "p_end_at" timestamp with time zone, "p_is_active" boolean) TO "service_role";



REVOKE ALL ON FUNCTION "public"."validate_academic_master_record"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."validate_academic_master_record"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."validate_test_schedule"("p_tenant" "uuid", "p_section" "uuid", "p_id" "uuid", "p_date" "date", "p_start" time without time zone, "p_end" time without time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."validate_test_schedule"("p_tenant" "uuid", "p_section" "uuid", "p_id" "uuid", "p_date" "date", "p_start" time without time zone, "p_end" time without time zone) TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."academic_years" TO "service_role";



GRANT ALL ON TABLE "public"."admin_audit_log" TO "service_role";



GRANT ALL ON TABLE "public"."ai_responses" TO "service_role";



GRANT ALL ON TABLE "public"."auth_consumed_password_recovery_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."auth_security_events" TO "service_role";



GRANT ALL ON TABLE "public"."campuses" TO "service_role";



GRANT ALL ON TABLE "public"."chunk_embeddings" TO "service_role";



GRANT ALL ON TABLE "public"."conversations" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."course_offerings" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."courses" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."departments" TO "service_role";



GRANT ALL ON TABLE "public"."document_processing_runs" TO "service_role";



GRANT ALL ON TABLE "public"."document_versions" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."email_delivery_attempts" TO "service_role";



GRANT ALL ON TABLE "public"."email_delivery_events" TO "service_role";



GRANT ALL ON SEQUENCE "public"."email_outbox_delivery_sequence_seq" TO "service_role";



GRANT ALL ON TABLE "public"."faculty_attendance_import_rows" TO "service_role";



GRANT ALL ON TABLE "public"."faculty_attendance_imports" TO "service_role";



GRANT ALL ON TABLE "public"."faculty_attendance_records" TO "service_role";



GRANT ALL ON TABLE "public"."faculty_attendance_rosters" TO "service_role";



GRANT ALL ON TABLE "public"."faculty_attendance_sessions" TO "service_role";



GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."faculty_responsibilities" TO "service_role";



GRANT ALL ON TABLE "public"."faculty_section_assignments" TO "service_role";



GRANT ALL ON TABLE "public"."faqs" TO "service_role";



GRANT ALL ON TABLE "public"."institution_join_requests" TO "service_role";



GRANT ALL ON TABLE "public"."institution_membership_requests" TO "service_role";



GRANT ALL ON TABLE "public"."institutions" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_sources" TO "service_role";



GRANT ALL ON TABLE "public"."message_citations" TO "service_role";



GRANT ALL ON TABLE "public"."messages" TO "service_role";



GRANT ALL ON TABLE "public"."notices" TO "service_role";



GRANT ALL ON TABLE "public"."organizations" TO "service_role";



GRANT ALL ON TABLE "public"."permissions" TO "service_role";



GRANT ALL ON TABLE "public"."platform_admin_invitations" TO "service_role";



GRANT ALL ON TABLE "public"."platform_institution_audit_log" TO "service_role";



GRANT ALL ON TABLE "public"."platform_role_audit_log" TO "service_role";



GRANT ALL ON TABLE "public"."platform_super_admin_invitations" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."program_courses" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."programs" TO "service_role";



GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."responsibility_definitions" TO "service_role";



GRANT SELECT,REFERENCES,TRIGGER,TRUNCATE,MAINTAIN ON TABLE "public"."responsibility_permissions" TO "service_role";



GRANT ALL ON TABLE "public"."retrieval_operations" TO "service_role";



GRANT ALL ON TABLE "public"."retrieved_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."role_permissions" TO "service_role";



GRANT ALL ON TABLE "public"."roles" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."sections" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,TRIGGER,MAINTAIN,UPDATE ON TABLE "public"."semesters" TO "service_role";



GRANT ALL ON TABLE "public"."student_attendance" TO "service_role";



GRANT ALL ON TABLE "public"."student_notifications" TO "service_role";



GRANT ALL ON TABLE "public"."student_result_items" TO "service_role";



GRANT ALL ON TABLE "public"."student_results" TO "service_role";



GRANT ALL ON TABLE "public"."students" TO "service_role";



GRANT ALL ON TABLE "public"."test_results" TO "service_role";



GRANT ALL ON TABLE "public"."test_types" TO "service_role";



GRANT ALL ON TABLE "public"."user_permission_grants" TO "service_role";



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








CREATE OR REPLACE FUNCTION "public"."test_results_tenant_guard"()
RETURNS "trigger"
LANGUAGE "plpgsql"
SECURITY DEFINER SET search_path = public, pg_temp
AS $function$
DECLARE
    t public.faculty_tests; r public.faculty_attendance_rosters; offering_record public.course_offerings;
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
        SELECT o.* INTO offering_record FROM sections s JOIN course_offerings o USING(course_offering_id) WHERE s.section_id=t.section_id;
        IF r.section_id IS DISTINCT FROM t.section_id OR r.institution_id IS DISTINCT FROM t.institution_id THEN
            RAISE EXCEPTION 'Result roster scope mismatch' USING ERRCODE='23514';
        END IF;
        IF TG_OP='UPDATE' AND (NEW.test_id IS DISTINCT FROM OLD.test_id OR NEW.roster_id IS DISTINCT FROM OLD.roster_id) THEN
            RAISE EXCEPTION 'Result identity is immutable' USING ERRCODE='23514'; END IF;
        IF current_setting('collegeai.test_write',true)='reconcile' AND TG_OP='UPDATE' AND
            (NEW.scored_marks IS DISTINCT FROM OLD.scored_marks OR NEW.mark_status IS DISTINCT FROM OLD.mark_status OR NEW.remarks IS DISTINCT FROM OLD.remarks) THEN
            RAISE EXCEPTION 'Reconciliation cannot modify marks' USING ERRCODE='42501'; END IF;
        NEW.student_id:=r.linked_student_id;
        NEW.institution_id:=t.institution_id; NEW.section_id:=t.section_id; NEW.course_id:=offering_record.course_id;
        NEW.academic_year_id:=offering_record.academic_year_id; NEW.semester_id:=offering_record.semester_id;
        NEW.test_name:=t.title; NEW.test_type:=t.test_type; NEW.max_marks:=t.max_marks;
        NEW.percentage:=round(NEW.scored_marks/t.max_marks*100,2); NEW.conducted_at:=t.scheduled_date::timestamp;
        NEW.status:=CASE WHEN t.status IN ('PUBLISHED','LOCKED') AND r.reconciliation_state<>'CONFLICT'
            AND r.roster_status='ACTIVE' AND EXISTS(SELECT 1 FROM students s WHERE s.student_id=r.linked_student_id
              AND s.institution_id=t.institution_id AND s.approval_status='approved' AND s.is_active AND s.status='active'
              AND (s.program_id IS NULL OR s.program_id=offering_record.program_id)
              AND (s.academic_year_id IS NULL OR s.academic_year_id=offering_record.academic_year_id
                OR public.academic_package_roster_has_placement(t.institution_id,r.roster_id,s.student_id))) THEN 'published' ELSE 'draft' END;
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

    RETURN NEW;
END;
$function$;

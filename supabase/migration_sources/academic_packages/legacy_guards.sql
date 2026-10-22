CREATE FUNCTION public.academic_package_roster_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE managed boolean; identity jsonb; offering public.course_offerings; internal_write boolean;
BEGIN
    internal_write := current_setting('app.academic_package_transaction', true) = pg_current_xact_id()::text;
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('attendance:' || NEW.institution_id::text, 0));
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF EXISTS (SELECT 1 FROM public.academic_subject_participation WHERE roster_id = OLD.roster_id)
            OR EXISTS (SELECT 1 FROM public.academic_class_subjects WHERE section_id = OLD.section_id)
            OR EXISTS (SELECT 1 FROM public.faculty_attendance_records WHERE roster_id = OLD.roster_id)
            OR EXISTS (SELECT 1 FROM public.test_results WHERE roster_id = OLD.roster_id)
            OR EXISTS (SELECT 1 FROM public.student_attendance WHERE student_id = OLD.linked_student_id AND section_id = OLD.section_id) THEN
            RAISE EXCEPTION 'Academic participation and history must be preserved' USING ERRCODE = '23514';
        END IF;
        RETURN OLD;
    END IF;
    IF TG_OP = 'UPDATE' AND NOT COALESCE(internal_write, false)
        AND (NEW.participation_active, NEW.participation_ended_at)
            IS DISTINCT FROM (OLD.participation_active, OLD.participation_ended_at) THEN
        RAISE EXCEPTION 'Participation is managed by package assignment' USING ERRCODE = '23514';
    END IF;
    SELECT EXISTS (SELECT 1 FROM public.academic_class_subjects WHERE section_id = NEW.section_id) INTO managed;
    IF managed AND NOT COALESCE(internal_write, false) THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION 'Use complete package assignment for this teaching group' USING ERRCODE = '23514';
        ELSIF (NEW.section_id, NEW.course_offering_id, NEW.semester_id, NEW.register_number, NEW.university_roll_number)
            IS DISTINCT FROM (OLD.section_id, OLD.course_offering_id, OLD.semester_id, OLD.register_number, OLD.university_roll_number) THEN
            RAISE EXCEPTION 'Package subject identity requires controlled review' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF managed AND TG_OP = 'UPDATE' AND NEW.linked_student_id IS DISTINCT FROM OLD.linked_student_id
        AND NEW.linked_student_id IS NOT NULL THEN
        identity := public.faculty_attendance_identity(NEW.institution_id, NEW.register_number, NEW.university_roll_number);
        IF COALESCE((identity->>'conflict')::boolean, true)
            OR identity->>'approval_status' IS DISTINCT FROM 'approved'
            OR NEW.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid THEN
            RAISE EXCEPTION 'Package roster link must match the approved academic identity' USING ERRCODE = '23514';
        END IF;
    END IF;
    -- Account reconciliation remains free to update linkage and approval state.
    -- New external identities must have the same academic eligibility as imports.
    IF TG_OP = 'INSERT' AND NOT COALESCE(internal_write, false) THEN
        SELECT * INTO offering FROM public.course_offerings WHERE course_offering_id = NEW.course_offering_id;
        identity := public.faculty_attendance_identity(NEW.institution_id, NEW.register_number, NEW.university_roll_number);
        IF COALESCE((identity->>'conflict')::boolean, true)
            OR (identity->>'program_id' IS NOT NULL AND (identity->>'program_id')::uuid <> offering.program_id)
            OR (identity->>'academic_year_id' IS NOT NULL AND (identity->>'academic_year_id')::uuid <> offering.academic_year_id) THEN
            RAISE EXCEPTION 'Roster student academic scope mismatch' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER academic_package_roster_write_guard BEFORE INSERT OR UPDATE OR DELETE
ON public.faculty_attendance_rosters FOR EACH ROW EXECUTE FUNCTION public.academic_package_roster_guard();

CREATE FUNCTION public.academic_package_participates_on(p_roster uuid, p_date date) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT NOT EXISTS (SELECT 1 FROM public.academic_subject_participation WHERE roster_id = p_roster)
        OR EXISTS (SELECT 1 FROM public.academic_subject_participation sp WHERE sp.roster_id = p_roster
            AND p_date >= (sp.started_at AT TIME ZONE 'UTC')::date
            AND (sp.ended_at IS NULL OR p_date <= (sp.ended_at AT TIME ZONE 'UTC')::date));
$$;

CREATE FUNCTION public.academic_package_event_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE roster uuid; event_date date; item jsonb := to_jsonb(NEW); matches uuid[];
BEGIN
    IF TG_TABLE_NAME = 'faculty_attendance_records' THEN
        roster := (item->>'roster_id')::uuid;
        SELECT session_date INTO event_date FROM public.faculty_attendance_sessions
        WHERE session_id = (item->>'session_id')::uuid;
    ELSIF TG_TABLE_NAME = 'test_results' AND item->>'roster_id' IS NOT NULL THEN
        roster := (item->>'roster_id')::uuid;
        IF item->>'test_id' IS NOT NULL THEN
            SELECT COALESCE(scheduled_date, (clock_timestamp() AT TIME ZONE 'UTC')::date)
            INTO event_date FROM public.faculty_tests WHERE test_id = (item->>'test_id')::uuid;
        END IF;
        event_date := COALESCE(event_date, ((item->>'conducted_at')::timestamptz AT TIME ZONE 'UTC')::date,
            (clock_timestamp() AT TIME ZONE 'UTC')::date);
    ELSE
        -- Legacy normalizers run later. Derive tenant through the canonical
        -- student, never the caller's possibly omitted/forged institution.
        SELECT array_agg(r.roster_id) INTO matches FROM public.faculty_attendance_rosters r
        JOIN public.students student ON student.student_id = (item->>'student_id')::uuid
        WHERE r.institution_id = student.institution_id AND r.section_id = (item->>'section_id')::uuid
          AND EXISTS (SELECT 1 FROM public.academic_subject_participation sp WHERE sp.roster_id = r.roster_id)
          AND (r.linked_student_id = student.student_id
            OR public.academic_package_roster_has_placement(student.institution_id, r.roster_id, student.student_id));
        IF COALESCE(cardinality(matches), 0) = 0 THEN RETURN NEW; END IF;
        IF cardinality(matches) <> 1 THEN
            RAISE EXCEPTION 'Legacy academic participation requires identity review' USING ERRCODE = '23514';
        END IF;
        roster := matches[1];
        event_date := CASE WHEN TG_TABLE_NAME = 'student_attendance' THEN (item->>'date')::date
            ELSE COALESCE(((item->>'conducted_at')::timestamptz AT TIME ZONE 'UTC')::date,
                (clock_timestamp() AT TIME ZONE 'UTC')::date) END;
    END IF;
    PERFORM 1 FROM public.faculty_attendance_rosters WHERE roster_id = roster FOR UPDATE;
    IF NOT public.academic_package_participates_on(roster, event_date) THEN
        RAISE EXCEPTION 'Student did not participate in this subject on the event date' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER academic_package_attendance_event BEFORE INSERT OR UPDATE ON public.faculty_attendance_records
    FOR EACH ROW EXECUTE FUNCTION public.academic_package_event_guard();
CREATE TRIGGER academic_package_marks_event BEFORE INSERT OR UPDATE ON public.test_results
    FOR EACH ROW EXECUTE FUNCTION public.academic_package_event_guard();
CREATE TRIGGER academic_package_legacy_attendance_event BEFORE INSERT OR UPDATE ON public.student_attendance
    FOR EACH ROW EXECUTE FUNCTION public.academic_package_event_guard();

-- A restrictive FK prevents attendance deletion even if an application check
-- raced another transaction. Existing child rows are neither moved nor deleted.
DO $$
DECLARE constraint_name text;
BEGIN
    FOR constraint_name IN SELECT conname FROM pg_catalog.pg_constraint
        WHERE conrelid = 'public.faculty_attendance_records'::regclass AND contype = 'f'
          AND confrelid = 'public.faculty_attendance_rosters'::regclass LOOP
        EXECUTE format('ALTER TABLE public.faculty_attendance_records DROP CONSTRAINT %I', constraint_name);
    END LOOP;
END;
$$;
ALTER TABLE public.faculty_attendance_records ADD CONSTRAINT academic_attendance_roster_history_fkey
    FOREIGN KEY (roster_id) REFERENCES public.faculty_attendance_rosters(roster_id) ON DELETE RESTRICT;
REVOKE DELETE, TRUNCATE ON public.faculty_attendance_rosters FROM service_role;
REVOKE UPDATE, DELETE, TRUNCATE ON public.admin_audit_log FROM service_role;

CREATE FUNCTION public.academic_package_no_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    RAISE EXCEPTION 'Academic history cannot be truncated' USING ERRCODE = '42501';
END;
$$;
CREATE TRIGGER academic_roster_no_truncate BEFORE TRUNCATE ON public.faculty_attendance_rosters
    FOR EACH STATEMENT EXECUTE FUNCTION public.academic_package_no_truncate();
CREATE TRIGGER academic_audit_no_truncate BEFORE TRUNCATE ON public.admin_audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION public.academic_package_no_truncate();

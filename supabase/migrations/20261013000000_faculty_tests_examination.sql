-- Shared assessment metadata; scores remain in the established test_results.
CREATE TABLE public.test_types (
    code text PRIMARY KEY CHECK (code ~ '^[a-z][a-z0-9_]{0,39}$'),
    name text NOT NULL, is_active boolean NOT NULL DEFAULT true
);
INSERT INTO public.test_types(code,name) VALUES
 ('quiz','Quiz'),('assignment','Assignment / Assessment'),('midterm','Mid-Term'),
 ('final','Semester / Final Exam'),('project','Project'),('internal','Internal Assessment'),
 ('external','External Exam'),('class_test','Class Test'),('model','Model Exam'),('practical','Practical');
ALTER TABLE public.test_results DROP CONSTRAINT test_results_test_type_check;
ALTER TABLE public.test_results ADD FOREIGN KEY(test_type) REFERENCES public.test_types(code);

CREATE TABLE public.faculty_tests (
    test_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    section_id uuid NOT NULL REFERENCES public.sections(section_id) ON DELETE RESTRICT,
    title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 160),
    test_type text NOT NULL REFERENCES public.test_types(code),
    description text CHECK (length(description)<=4000),
    max_marks numeric(8,2) NOT NULL CHECK (max_marks>0),
    passing_marks numeric(8,2) CHECK (passing_marks BETWEEN 0 AND max_marks),
    scheduled_date date, start_time time, end_time time,
    duration_minutes integer CHECK (duration_minutes BETWEEN 1 AND 1440),
    status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','SCHEDULED','ONGOING','COMPLETED','PUBLISHED','LOCKED','CANCELLED')),
    marks_state text NOT NULL DEFAULT 'DRAFT' CHECK (marks_state IN ('DRAFT','SUBMITTED')),
    version bigint NOT NULL DEFAULT 1,
    created_by uuid NOT NULL REFERENCES public.users(id), updated_by uuid NOT NULL REFERENCES public.users(id),
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((start_time IS NULL AND end_time IS NULL) OR
        (scheduled_date IS NOT NULL AND start_time IS NOT NULL AND end_time IS NOT NULL AND end_time>start_time)),
    CHECK (status IN ('DRAFT','CANCELLED') OR scheduled_date IS NOT NULL)
);
CREATE UNIQUE INDEX faculty_tests_duplicate ON public.faculty_tests(section_id,lower(btrim(title)),scheduled_date)
    NULLS NOT DISTINCT WHERE status<>'CANCELLED';
CREATE INDEX faculty_tests_scope ON public.faculty_tests(institution_id,section_id,scheduled_date);

ALTER TABLE public.test_results ALTER COLUMN student_id DROP NOT NULL;
ALTER TABLE public.test_results ADD COLUMN test_id uuid REFERENCES public.faculty_tests(test_id) ON DELETE RESTRICT,
    ADD COLUMN roster_id uuid REFERENCES public.faculty_attendance_rosters(roster_id) ON DELETE RESTRICT,
    ADD COLUMN mark_status text CHECK (mark_status IN ('present','absent','exempt','not_attempted','missing')),
    ADD COLUMN remarks text CHECK (length(remarks)<=1000),
    ADD CONSTRAINT test_results_identity CHECK (
      (test_id IS NULL AND roster_id IS NULL AND student_id IS NOT NULL) OR
      (test_id IS NOT NULL AND roster_id IS NOT NULL AND mark_status IS NOT NULL)),
    ADD CONSTRAINT test_results_explicit_score CHECK (test_id IS NULL OR
      ((mark_status='present' AND scored_marks IS NOT NULL) OR (mark_status<>'present' AND scored_marks IS NULL)));
ALTER TABLE public.test_results DROP CONSTRAINT test_results_student_course_test_sem_key;
CREATE UNIQUE INDEX test_results_legacy_unique ON public.test_results(student_id,course_id,test_name,academic_year_id,semester_id)
    WHERE test_id IS NULL;
CREATE UNIQUE INDEX test_results_test_roster ON public.test_results(test_id,roster_id) WHERE test_id IS NOT NULL;
CREATE UNIQUE INDEX test_results_test_student ON public.test_results(test_id,student_id) WHERE test_id IS NOT NULL AND student_id IS NOT NULL;

-- Reuse private staging tables. NULL test_id continues to mean attendance.
ALTER TABLE public.faculty_attendance_imports ADD COLUMN test_id uuid REFERENCES public.faculty_tests(test_id) ON DELETE RESTRICT;
INSERT INTO public.responsibility_permissions(responsibility_code,permission_id)
SELECT r.code,p.permission_id FROM public.responsibility_definitions r CROSS JOIN public.permissions p
WHERE r.code IN ('hod','class_in_charge') AND p.code='results.read' ON CONFLICT DO NOTHING;

ALTER TABLE public.faculty_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_results ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.faculty_tests,public.test_types FROM anon,authenticated;
REVOKE ALL ON public.test_results FROM anon,authenticated;
GRANT ALL ON public.faculty_tests,public.test_types TO service_role;

CREATE FUNCTION public.assert_faculty_academic_mutation(p_actor uuid, p_tenant uuid, p_section uuid, p_permission text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
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

CREATE OR REPLACE FUNCTION public.assert_faculty_attendance_mutation(p_actor uuid,p_tenant uuid,p_section uuid)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=public AS $$
 SELECT public.assert_faculty_academic_mutation(p_actor,p_tenant,p_section,'attendance.manage');
$$;

-- Generalization of the existing transactional teaching guard is appended
-- below by this migration; attendance retains its original public signature.

CREATE FUNCTION public.faculty_test_context_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public AS $$
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
CREATE TRIGGER faculty_test_context BEFORE INSERT OR UPDATE ON public.faculty_tests
FOR EACH ROW EXECUTE FUNCTION public.faculty_test_context_guard();

CREATE FUNCTION public.guard_workflow_result_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.test_id IS NOT NULL THEN RAISE EXCEPTION 'Assessment history cannot be deleted' USING ERRCODE='42501'; END IF;
 RETURN OLD;
END; $$;
CREATE TRIGGER workflow_result_delete BEFORE DELETE ON public.test_results
FOR EACH ROW EXECUTE FUNCTION public.guard_workflow_result_delete();

CREATE FUNCTION public.assert_test_version(p_actor uuid,p_tenant uuid,p_test uuid,p_version bigint)
RETURNS public.faculty_tests LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE FUNCTION public.validate_test_schedule(p_tenant uuid,p_section uuid,p_id uuid,p_date date,p_start time,p_end time)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE FUNCTION public.save_faculty_test(p_actor uuid,p_tenant uuid,p_section uuid,p_data jsonb,
 p_test uuid DEFAULT NULL,p_version bigint DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE FUNCTION public.save_faculty_test_marks(p_actor uuid,p_tenant uuid,p_test uuid,p_version bigint,p_rows jsonb,p_reason text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE FUNCTION public.transition_faculty_test(p_actor uuid,p_tenant uuid,p_test uuid,p_version bigint,p_action text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

-- The same staged table/rows and append-only audit support spreadsheet marks.
CREATE FUNCTION public.stage_faculty_test_import(p_actor uuid,p_tenant uuid,p_test uuid,p_filename text,p_strategy text,p_summary jsonb,p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE FUNCTION public.review_faculty_test_import(p_actor uuid,p_tenant uuid,p_import uuid,p_updated_at timestamptz,p_summary jsonb,p_rows jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE FUNCTION public.commit_faculty_test_import(p_actor uuid,p_tenant uuid,p_import uuid,p_updated_at timestamptz,p_version bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
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

CREATE OR REPLACE FUNCTION "public"."test_results_tenant_guard"()
RETURNS "trigger"
LANGUAGE "plpgsql"
AS $function$
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
$function$;


CREATE FUNCTION public.reconcile_faculty_test_roster() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE previous_setting text:=current_setting('collegeai.test_write',true);
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||NEW.institution_id::text,0));
 PERFORM set_config('collegeai.test_write','reconcile',true);
 UPDATE test_results SET student_id=NEW.linked_student_id WHERE roster_id=NEW.roster_id AND test_id IS NOT NULL;
 PERFORM set_config('collegeai.test_write',coalesce(previous_setting,''),true);
 RETURN NEW;
END; $$;
CREATE TRIGGER reconcile_faculty_test_roster AFTER UPDATE OF linked_student_id,reconciliation_state,roster_status
 ON public.faculty_attendance_rosters FOR EACH ROW EXECUTE FUNCTION public.reconcile_faculty_test_roster();

-- Registration still uses the attendance reconciler. Lifecycle changes which
-- do not alter a roster must also refresh student visibility without changing marks.
CREATE FUNCTION public.refresh_student_test_visibility() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$
DECLARE previous_setting text:=current_setting('collegeai.test_write',true);
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended('attendance:'||NEW.institution_id::text,0));
 PERFORM set_config('collegeai.test_write','reconcile',true);
 UPDATE test_results SET student_id=student_id WHERE student_id=NEW.student_id AND test_id IS NOT NULL;
 PERFORM set_config('collegeai.test_write',coalesce(previous_setting,''),true);
 RETURN NEW;
END; $$;
CREATE TRIGGER test_student_visibility AFTER UPDATE OF approval_status,is_active,status,program_id,academic_year_id ON public.students
 FOR EACH ROW EXECUTE FUNCTION public.refresh_student_test_visibility();
REVOKE ALL ON FUNCTION public.refresh_student_test_visibility() FROM PUBLIC,anon,authenticated;

-- Prevent using an attendance RPC to mutate assessment staging (and vice versa).
CREATE FUNCTION public.guard_test_import_workflow() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER guard_test_import BEFORE INSERT OR UPDATE OR DELETE ON public.faculty_attendance_imports
 FOR EACH ROW EXECUTE FUNCTION public.guard_test_import_workflow();
CREATE TRIGGER guard_test_import_rows BEFORE INSERT OR UPDATE OR DELETE ON public.faculty_attendance_import_rows
 FOR EACH ROW EXECUTE FUNCTION public.guard_test_import_workflow();
REVOKE ALL ON FUNCTION public.assert_faculty_academic_mutation(uuid,uuid,uuid,text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.assert_test_version(uuid,uuid,uuid,bigint) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.validate_test_schedule(uuid,uuid,uuid,date,time,time) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.save_faculty_test(uuid,uuid,uuid,jsonb,uuid,bigint) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.transition_faculty_test(uuid,uuid,uuid,bigint,text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.stage_faculty_test_import(uuid,uuid,uuid,text,text,jsonb,jsonb) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.review_faculty_test_import(uuid,uuid,uuid,timestamptz,jsonb,jsonb) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.commit_faculty_test_import(uuid,uuid,uuid,timestamptz,bigint) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.reconcile_faculty_test_roster() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.faculty_test_context_guard() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.guard_workflow_result_delete() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.guard_test_import_workflow() FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.save_faculty_test(uuid,uuid,uuid,jsonb,uuid,bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.save_faculty_test_marks(uuid,uuid,uuid,bigint,jsonb,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.transition_faculty_test(uuid,uuid,uuid,bigint,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.stage_faculty_test_import(uuid,uuid,uuid,text,text,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.review_faculty_test_import(uuid,uuid,uuid,timestamptz,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_faculty_test_import(uuid,uuid,uuid,timestamptz,bigint) TO service_role;

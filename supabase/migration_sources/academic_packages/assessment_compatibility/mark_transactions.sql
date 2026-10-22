CREATE OR REPLACE FUNCTION public.save_faculty_test_marks(p_actor uuid,p_tenant uuid,p_test uuid,p_version bigint,p_rows jsonb,p_reason text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
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
   identity:=public.academic_package_identity_for_roster(p_tenant,r.roster_id);
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

CREATE OR REPLACE FUNCTION public.transition_faculty_test(p_actor uuid,p_tenant uuid,p_test uuid,p_version bigint,p_action text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
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
   FOR checked_roster IN SELECT * FROM faculty_attendance_rosters WHERE institution_id=p_tenant AND section_id=t.section_id AND roster_status<>'INACTIVE'
       AND public.academic_package_participates_on(roster_id,t.scheduled_date) FOR SHARE LOOP
     identity:=public.academic_package_identity_for_roster(p_tenant,checked_roster.roster_id);
     IF (identity->>'conflict')::boolean OR
       (identity->>'program_id' IS NOT NULL AND (identity->>'program_id')::uuid<>co.program_id) OR
       (identity->>'academic_year_id' IS NOT NULL AND (identity->>'academic_year_id')::uuid<>co.academic_year_id) OR
       (checked_roster.linked_student_id IS NOT NULL AND checked_roster.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid) THEN
       RAISE EXCEPTION 'Roster identity conflicts prevent submission/publication' USING ERRCODE='23514'; END IF;
   END LOOP;
   IF NOT EXISTS(SELECT 1 FROM test_results WHERE test_id=p_test) OR EXISTS(
     SELECT 1 FROM faculty_attendance_rosters r LEFT JOIN test_results m ON m.roster_id=r.roster_id AND m.test_id=p_test
     WHERE r.section_id=t.section_id AND r.institution_id=p_tenant AND r.roster_status<>'INACTIVE'
       AND public.academic_package_participates_on(r.roster_id,t.scheduled_date)
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

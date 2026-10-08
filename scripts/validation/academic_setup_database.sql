-- Isolated, disposable replay only. Every contract fixture is rolled back.
BEGIN;
SET LOCAL search_path = public, extensions;
SELECT set_config('request.jwt.claim.role','service_role',true);
DO $$
DECLARE
    org uuid:=gen_random_uuid(); tenant uuid:=gen_random_uuid(); foreign_tenant uuid:=gen_random_uuid();
    actor uuid:=gen_random_uuid(); faculty uuid:=gen_random_uuid();
    d jsonb; p jsonb; y jsonb; s jsonb; c jsonb; pc jsonb; o jsonb; sec jsonb;
    fd uuid:=gen_random_uuid(); fc uuid:=gen_random_uuid(); item jsonb; entity text; key text;
    before_count bigint; assignment uuid;
BEGIN
    INSERT INTO public.organizations(organization_id,name,organization_code,official_email,contact_information,status)
    VALUES(org,'Isolated contract','AS-'||org::text,'contract@example.invalid','Disposable verification','active');
    INSERT INTO public.institutions(institution_id,name,code,organization_id,status)
    VALUES(tenant,'Isolated institution','AS-'||tenant::text,org,'active'),(foreign_tenant,'Foreign isolated institution','AS-'||foreign_tenant::text,org,'active');
    INSERT INTO auth.users(id,email) VALUES(actor,actor||'@example.invalid'),(faculty,faculty||'@example.invalid');
    INSERT INTO public.users(id,auth_user_id,email,first_name,last_name)
    SELECT id,id,email,'Contract','User' FROM auth.users WHERE id IN(actor,faculty);
    INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
    SELECT actor,id,'institution',tenant,org FROM public.roles WHERE name='admin';
    INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
    SELECT faculty,id,'institution',tenant,org FROM public.roles WHERE name='faculty';
    INSERT INTO public.departments(department_id,institution_id,name,code) VALUES(fd,foreign_tenant,'Foreign department','F');
    INSERT INTO public.courses(course_id,department_id,name,code) VALUES(fc,fd,'Foreign subject','F');
    d:=public.manage_academic_master_record(actor,tenant,'departments',NULL,'{"name":"Science","code":"SCI"}');
    p:=public.manage_academic_master_record(actor,tenant,'programs',NULL,jsonb_build_object('department_id',d->>'department_id','name','Science degree','code','BS','degree_type','BSc','duration_years',3));
    y:=public.manage_academic_master_record(actor,tenant,'academic_years',NULL,'{"name":"2026-27","code":"Y26","start_date":"2026-07-01","end_date":"2027-06-30","is_current":true}');
    s:=public.manage_academic_master_record(actor,tenant,'semesters',NULL,jsonb_build_object('academic_year_id',y->>'academic_year_id','name','Semester 1','code','S1','semester_number',1,'start_date','2026-07-01','end_date','2026-12-31'));
    c:=public.manage_academic_master_record(actor,tenant,'courses',NULL,jsonb_build_object('department_id',d->>'department_id','name','Mathematics','code','MATH','credits',3));
    pc:=public.manage_academic_master_record(actor,tenant,'program_courses',NULL,jsonb_build_object('program_id',p->>'program_id','course_id',c->>'course_id','course_type','core'));
    o:=public.manage_academic_master_record(actor,tenant,'course_offerings',NULL,jsonb_build_object('program_id',p->>'program_id','course_id',c->>'course_id','academic_year_id',y->>'academic_year_id','semester_id',s->>'semester_id'));
    sec:=public.manage_academic_master_record(actor,tenant,'sections',NULL,jsonb_build_object('course_offering_id',o->>'course_offering_id','name','Section A','code','A'));
    IF (SELECT count(*) FROM public.admin_audit_log WHERE institution_id=tenant AND action LIKE 'academic.%.create')<>8 THEN RAISE EXCEPTION 'Create audits missing'; END IF;
    FOR entity,item,key IN SELECT * FROM (VALUES
      ('departments',d,'department_id'),('programs',p,'program_id'),('academic_years',y,'academic_year_id'),('semesters',s,'semester_id'),
      ('courses',c,'course_id'),('program_courses',pc,'program_course_id'),('course_offerings',o,'course_offering_id'),('sections',sec,'section_id')) t(entity,item,key)
    LOOP
      PERFORM public.manage_academic_master_record(actor,tenant,entity,(item->>key)::uuid,'{"is_active":true}');
      IF NOT EXISTS(SELECT 1 FROM public.admin_audit_log a WHERE a.institution_id=tenant AND a.table_name=entity AND a.record_id=(item->>key)::uuid AND a.record_data->'before' IS NOT NULL AND a.record_data->'after' IS NOT NULL)
      THEN RAISE EXCEPTION 'Update audit missing for %',entity; END IF;
    END LOOP;
    -- Existing assignment RPC consumes the exact section produced by setup.
    assignment:=public.create_faculty_teaching_assignment(actor,tenant,faculty,(sec->>'section_id')::uuid,now()-interval '1 day',NULL,true);
    IF NOT EXISTS(SELECT 1 FROM public.faculty_section_assignments a WHERE a.assignment_id=assignment AND a.section_id=(sec->>'section_id')::uuid) THEN RAISE EXCEPTION 'Assignment integration failed'; END IF;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'departments',NULL,'{"name":"Duplicate","code":" sci "}');
      RAISE EXCEPTION 'Normalized duplicate allowed';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'departments',fd,'{"name":"Stolen"}');
      RAISE EXCEPTION 'Cross-tenant IDOR allowed';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'programs',NULL,jsonb_build_object('department_id',fd,'name','Stolen','code','X','degree_type','X','duration_years',1));
      RAISE EXCEPTION 'Cross-tenant parent allowed';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'program_courses',NULL,jsonb_build_object('program_id',p->>'program_id','course_id',fc,'course_type','core'));
      RAISE EXCEPTION 'Foreign subject allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
      INSERT INTO public.program_courses(program_id,course_id,course_type) VALUES((p->>'program_id')::uuid,fc,'core');
      RAISE EXCEPTION 'Direct cross-tenant curriculum allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(faculty,tenant,'departments',NULL,'{"name":"Forbidden","code":"BAD"}');
      RAISE EXCEPTION 'Faculty gained global academic authority';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'departments',NULL,jsonb_build_object('name','Forged','code','BAD','institution_id',foreign_tenant));
      RAISE EXCEPTION 'Forged control field allowed';
    EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
    BEGIN
      UPDATE public.programs SET department_id=fd WHERE program_id=(p->>'program_id')::uuid;
      RAISE EXCEPTION 'Direct reparenting allowed';
    EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'academic_years',NULL,'{"name":"Overlap","code":"OVER","start_date":"2027-01-01","end_date":"2028-01-01"}');
      RAISE EXCEPTION 'Overlapping active years allowed';
    EXCEPTION WHEN exclusion_violation THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'academic_years',NULL,'{"name":"Next","code":"NEXT","start_date":"2027-07-01","end_date":"2028-06-30","is_current":true}');
      RAISE EXCEPTION 'Two current years allowed';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'semesters',(s->>'semester_id')::uuid,'{"end_date":"2028-01-01"}');
      RAISE EXCEPTION 'Semester outside year allowed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'academic_years',(y->>'academic_year_id')::uuid,'{"end_date":"2026-08-01"}');
      RAISE EXCEPTION 'Year excluded existing term';
    EXCEPTION WHEN check_violation THEN NULL; END;
    PERFORM public.manage_academic_master_record(actor,tenant,'departments',(d->>'department_id')::uuid,'{"is_active":false}');
    IF NOT EXISTS(SELECT 1 FROM public.programs WHERE program_id=(p->>'program_id')::uuid) OR NOT EXISTS(SELECT 1 FROM public.sections WHERE section_id=(sec->>'section_id')::uuid) THEN RAISE EXCEPTION 'Deactivation lost dependent history'; END IF;
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'programs',NULL,jsonb_build_object('department_id',d->>'department_id','name','Inactive parent','code','BAD','degree_type','BSc','duration_years',3));
      RAISE EXCEPTION 'Inactive parent accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    PERFORM public.manage_academic_master_record(actor,tenant,'departments',(d->>'department_id')::uuid,'{"is_active":true}');
    -- Revocation at the database permission matrix remains effective.
    DELETE FROM public.role_permissions rp USING public.permissions permission,public.roles r
      WHERE rp.role_id=r.id AND r.name='admin' AND rp.permission_id=permission.permission_id AND permission.code='departments.manage';
    BEGIN
      PERFORM public.manage_academic_master_record(actor,tenant,'departments',NULL,'{"name":"Revoked","code":"BAD"}');
      RAISE EXCEPTION 'Revoked permission allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
    IF (SELECT count(*) FROM public.students WHERE institution_id=tenant)<>0 THEN RAISE EXCEPTION 'Setup created a student'; END IF;
    FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','semesters','courses','program_courses','course_offerings','sections'] LOOP
      IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid=('public.'||entity)::regclass)
        OR has_table_privilege('anon','public.'||entity,'SELECT') OR has_table_privilege('authenticated','public.'||entity,'SELECT')
        OR has_table_privilege('authenticated','public.'||entity,'INSERT') OR has_table_privilege('authenticated','public.'||entity,'UPDATE')
        OR has_table_privilege('service_role','public.'||entity,'DELETE') OR NOT has_table_privilege('service_role','public.'||entity,'SELECT')
      THEN RAISE EXCEPTION 'Privilege/RLS failure for %',entity; END IF;
    END LOOP;
    IF has_function_privilege('anon','public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)','EXECUTE') OR has_function_privilege('authenticated','public.academic_master_tenant(text,uuid)','EXECUTE') THEN RAISE EXCEPTION 'Browser RPC exposure'; END IF;
    RAISE NOTICE 'PASS: all eight entities, audit, hierarchy, tenant/IDOR, authorization, duplicates/dates, archive, assignment integration, RLS/privileges';
END;
$$;
SET LOCAL ROLE anon;
DO $$
DECLARE entity text;
BEGIN
  FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','semesters','courses','program_courses','course_offerings','sections'] LOOP
    BEGIN
      EXECUTE format('SELECT count(*) FROM public.%I',entity);
      RAISE EXCEPTION 'Anonymous read allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
  END LOOP;
END;
$$;
RESET ROLE;
SET LOCAL ROLE authenticated;
DO $$
DECLARE entity text;
BEGIN
  FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','semesters','courses','program_courses','course_offerings','sections'] LOOP
    BEGIN
      EXECUTE format('SELECT count(*) FROM public.%I',entity);
      RAISE EXCEPTION 'Authenticated direct read allowed';
    EXCEPTION WHEN insufficient_privilege THEN NULL; END;
  END LOOP;
END;
$$;
RESET ROLE;
ROLLBACK;

-- Prove failed audit rolls back the academic mutation in the same transaction.
BEGIN;
SELECT set_config('request.jwt.claim.role','service_role',true);
CREATE FUNCTION public.academic_contract_reject_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Injected audit failure'; END; $$;
CREATE TRIGGER academic_contract_reject_audit BEFORE INSERT ON public.admin_audit_log FOR EACH ROW EXECUTE FUNCTION public.academic_contract_reject_audit();
DO $$
DECLARE actor uuid; tenant uuid;
BEGIN
  SELECT ur.user_id,ur.scope_id INTO actor,tenant FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id JOIN public.users u ON u.id=ur.user_id JOIN public.institutions i ON i.institution_id=ur.scope_id
  WHERE r.name='admin' AND ur.scope_type='institution' AND u.status='active' AND i.status='active' AND i.is_active LIMIT 1;
  IF actor IS NULL THEN RAISE EXCEPTION 'Replay administrator unavailable for audit failure test'; END IF;
  BEGIN
    PERFORM public.manage_academic_master_record(actor,tenant,'departments',NULL,'{"name":"Audit failure contract","code":"AUDIT-FAILURE-CONTRACT"}');
    RAISE EXCEPTION 'Expected audit failure';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM<>'Injected audit failure' THEN RAISE; END IF;
  END;
  IF EXISTS(SELECT 1 FROM public.departments WHERE institution_id=tenant AND code='AUDIT-FAILURE-CONTRACT') THEN RAISE EXCEPTION 'Unaudited mutation persisted'; END IF;
  RAISE NOTICE 'PASS: audit failure rolls back academic mutation';
END; $$;
ROLLBACK;

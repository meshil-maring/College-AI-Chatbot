CREATE EXTENSION IF NOT EXISTS plpgsql_check WITH SCHEMA extensions;
DO $$
DECLARE item regprocedure; entity text; diagnostic record; findings integer:=0;
BEGIN
  FOREACH item IN ARRAY ARRAY[
    'public.academic_master_tenant(text,uuid)'::regprocedure,
    'public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb)'::regprocedure
  ] LOOP
    FOR diagnostic IN SELECT * FROM extensions.plpgsql_check_function_tb(item, fatal_errors:=false) LOOP
      RAISE NOTICE '%: % % %',item,diagnostic.level,diagnostic.sqlstate,diagnostic.message;
      IF diagnostic.level IN ('error','fatal error') THEN findings:=findings+1; END IF;
    END LOOP;
  END LOOP;
  FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','semesters','courses','program_courses','course_offerings','sections'] LOOP
    FOR diagnostic IN SELECT * FROM extensions.plpgsql_check_function_tb('public.validate_academic_master_record()'::regprocedure,('public.'||entity)::regclass, fatal_errors:=false) LOOP
      RAISE NOTICE 'trigger on %: % % %',entity,diagnostic.level,diagnostic.sqlstate,diagnostic.message;
      IF diagnostic.level IN ('error','fatal error') THEN findings:=findings+1; END IF;
    END LOOP;
  END LOOP;
  IF findings<>0 THEN RAISE EXCEPTION 'Academic SQL lint: % errors',findings; END IF;
  RAISE NOTICE 'ACADEMIC SQL LINT PASS: two functions and validation trigger across eight tables';
END; $$;

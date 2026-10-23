-- Read-only checks for the retained identity/approval schema after removal.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT jsonb_build_object(
    'student_academic_columns',(SELECT COALESCE(jsonb_agg(column_name ORDER BY column_name),'[]'::jsonb)
        FROM information_schema.columns WHERE table_schema='public' AND table_name='students'
        AND column_name IN('program_id','academic_year_id')),
    'student_identity_columns',(SELECT COALESCE(jsonb_agg(column_name ORDER BY column_name),'[]'::jsonb)
        FROM information_schema.columns WHERE table_schema='public' AND table_name='students'
        AND column_name IN('student_id','user_id','institution_id','email','approval_status','status','is_active')),
    'approval_rpc_present',to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NOT NULL,
    'approval_authenticated_execute',CASE WHEN to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NULL
        THEN NULL ELSE has_function_privilege('authenticated','public.b05_approve_student(uuid,uuid,uuid,uuid)','EXECUTE') END,
    'approval_service_role_execute',CASE WHEN to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NULL
        THEN NULL ELSE has_function_privilege('service_role','public.b05_approve_student(uuid,uuid,uuid,uuid)','EXECUTE') END,
    'retired_permissions_remaining',(SELECT count(*) FROM public.permissions
        WHERE code ~ '^(academic\.|attendance\.|results\.|faculty\.assignments\.|departments\.|courses\.|subjects\.|semesters\.|academic_years\.)'),
    'release_ledger_count',(SELECT count(*) FROM supabase_migrations.schema_migrations WHERE version='20261023000000')
) AS academic_decommission_postchecks;
ROLLBACK;

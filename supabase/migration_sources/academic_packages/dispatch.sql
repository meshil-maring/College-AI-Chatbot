CREATE FUNCTION public.academic_package_command(p_actor_user_id uuid, p_institution_id uuid, p_operation text, p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE placement uuid; assignment public.academic_package_assignments;
BEGIN
    PERFORM public.academic_package_actor(p_actor_user_id, p_institution_id);
    IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' THEN
        RAISE EXCEPTION 'Command payload must be an object' USING ERRCODE = '22023';
    END IF;
    -- Same first lock as existing attendance/import RPCs; all participating
    -- writers serialize before taking row/capacity locks in a consistent order.
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('attendance:' || p_institution_id::text, 0));
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-package:' || p_institution_id::text, 0));
    PERFORM set_config('app.academic_package_transaction', pg_current_xact_id()::text, true);
    PERFORM public.academic_package_actor(p_actor_user_id, p_institution_id);
    IF p_operation IN ('save_curriculum','set_curriculum_subject','save_package') THEN
        RETURN public.academic_package_curriculum_command(p_actor_user_id, p_institution_id, p_operation, p_payload);
    ELSIF p_operation IN ('save_class','set_class_package','set_class_subject','set_class_responsibility') THEN
        RETURN public.academic_package_class_command(p_actor_user_id, p_institution_id, p_operation, p_payload);
    ELSIF p_operation = 'place_student' THEN
        RETURN public.academic_package_place(p_actor_user_id, p_institution_id, p_payload);
    ELSIF p_operation = 'prepare_class_teaching' THEN
        RETURN public.academic_package_prepare_teaching(p_actor_user_id, p_institution_id, (p_payload->>'class_id')::uuid);
    ELSIF p_operation = 'assign_package' THEN
        RETURN public.academic_package_apply(p_actor_user_id, p_institution_id,
            (p_payload->>'placement_id')::uuid, (p_payload->>'package_id')::uuid);
    ELSIF p_operation = 'change_package' THEN
        SELECT a.* INTO assignment FROM public.academic_package_assignments a
        JOIN public.academic_class_placements cp USING(placement_id) JOIN public.academic_classes c USING(class_id)
        WHERE a.assignment_id = (p_payload->>'assignment_id')::uuid AND c.institution_id = p_institution_id;
        IF NOT FOUND THEN RAISE EXCEPTION 'Assignment not found' USING ERRCODE = 'P0002'; END IF;
        RETURN public.academic_package_apply(p_actor_user_id, p_institution_id, assignment.placement_id,
            (p_payload->>'package_id')::uuid, (p_payload->>'expected_revision')::integer, p_payload->>'reason');
    ELSIF p_operation IN ('request_change','review_request') THEN
        RETURN public.academic_package_request_command(p_actor_user_id, p_institution_id, p_operation, p_payload);
    END IF;
    RAISE EXCEPTION 'Unknown academic package operation' USING ERRCODE = '22023';
END;
$$;

DO $$
DECLARE routine regprocedure;
BEGIN
    FOR routine IN SELECT p.oid::regprocedure FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND (p.proname LIKE 'academic_package_%'
            OR p.proname IN ('academic_legacy_section_authorize','assign_student_subject','delete_academic_roster')) LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, anon, authenticated, service_role', routine);
    END LOOP;
END;
$$;
GRANT EXECUTE ON FUNCTION public.academic_package_catalogue(uuid,uuid),
    public.academic_package_command(uuid,uuid,text,jsonb),
    public.assign_student_subject(uuid,uuid,uuid,uuid,text), public.delete_academic_roster(uuid,uuid,uuid),
    public.academic_package_roster_context(uuid,uuid[]),
    public.academic_package_offering_eligibility(uuid,uuid) TO service_role;
NOTIFY pgrst, 'reload schema';

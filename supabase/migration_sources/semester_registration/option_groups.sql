CREATE FUNCTION public.manage_curriculum_choice_group(
    p_actor uuid, p_tenant uuid, p_group uuid, p_payload jsonb, p_delete boolean DEFAULT false
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE group_id uuid:=COALESCE(p_group,gen_random_uuid()); version_id uuid; stage_id uuid;
    version_row jsonb; stage_row jsonb; option_row jsonb; option_id uuid;
    subject_id uuid; subject_row record; previous_row jsonb;
BEGIN
    PERFORM public.assert_academic_foundation_actor(p_actor,p_tenant,'courses');
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    IF p_group IS NOT NULL THEN
        SELECT to_jsonb(g) INTO previous_row FROM public.curriculum_choice_groups g
        WHERE choice_group_id=p_group AND institution_id=p_tenant FOR UPDATE;
        IF previous_row IS NULL THEN
            RAISE EXCEPTION 'Option group not found' USING ERRCODE='P0002';
        END IF;
    END IF;
    version_id:=COALESCE((previous_row->>'curriculum_version_id')::uuid,(p_payload->>'curriculum_version_id')::uuid);
    stage_id:=COALESCE((previous_row->>'program_semester_id')::uuid,(p_payload->>'program_semester_id')::uuid);
    version_row:=public.academic_structure_parent('curriculum_versions',version_id,p_tenant);
    stage_row:=public.academic_structure_parent('program_semesters',stage_id,p_tenant);
    IF version_row->>'status'<>'draft' OR version_row->>'program_id'<>stage_row->>'program_id'
       OR (stage_row->>'semester_number')::integer>(version_row->>'total_semesters')::integer THEN
        RAISE EXCEPTION 'Edit option groups only in a matching draft curriculum' USING ERRCODE='23514';
    END IF;
    IF p_delete THEN
        DELETE FROM public.curriculum_choice_groups WHERE choice_group_id=p_group AND institution_id=p_tenant;
    ELSE
        IF jsonb_typeof(p_payload->'options') IS DISTINCT FROM 'array'
           OR jsonb_array_length(p_payload->'options') NOT BETWEEN 2 AND 20 THEN
            RAISE EXCEPTION 'Provide two or more complete options' USING ERRCODE='22023';
        END IF;
        IF p_group IS NULL THEN
            INSERT INTO public.curriculum_choice_groups(choice_group_id,institution_id,curriculum_version_id,program_semester_id,name)
            VALUES(group_id,p_tenant,version_id,stage_id,btrim(p_payload->>'name'));
        ELSE
            IF (p_payload->>'curriculum_version_id')::uuid IS DISTINCT FROM version_id
               OR (p_payload->>'program_semester_id')::uuid IS DISTINCT FROM stage_id THEN
                RAISE EXCEPTION 'Option group relationships are immutable' USING ERRCODE='22023';
            END IF;
            UPDATE public.curriculum_choice_groups SET name=btrim(p_payload->>'name') WHERE choice_group_id=group_id;
            DELETE FROM public.curriculum_choice_options WHERE choice_group_id=group_id;
        END IF;
        FOR option_row IN SELECT value FROM jsonb_array_elements(p_payload->'options') LOOP
            IF jsonb_typeof(option_row->'curriculum_subject_ids') IS DISTINCT FROM 'array'
               OR jsonb_array_length(option_row->'curriculum_subject_ids') NOT BETWEEN 1 AND 64 THEN
                RAISE EXCEPTION 'Every option requires subjects' USING ERRCODE='22023';
            END IF;
            INSERT INTO public.curriculum_choice_options(institution_id,choice_group_id,name)
            VALUES(p_tenant,group_id,btrim(option_row->>'name')) RETURNING choice_option_id INTO option_id;
            FOR subject_id IN SELECT value::uuid FROM jsonb_array_elements_text(option_row->'curriculum_subject_ids') LOOP
                SELECT * INTO subject_row FROM public.curriculum_subjects
                WHERE curriculum_subject_id=subject_id AND institution_id=p_tenant;
                IF NOT FOUND OR subject_row.curriculum_version_id<>version_id
                   OR subject_row.program_semester_id<>stage_id OR NOT subject_row.is_active OR subject_row.is_required THEN
                    RAISE EXCEPTION 'Option subjects must be active optional mappings in this semester' USING ERRCODE='23514';
                END IF;
                IF EXISTS(SELECT 1 FROM public.curriculum_choice_subjects cs
                    JOIN public.curriculum_choice_options co USING(choice_option_id)
                    WHERE cs.curriculum_subject_id=subject_id AND co.choice_group_id<>group_id) THEN
                    RAISE EXCEPTION 'Subject already belongs to another choice group' USING ERRCODE='23514';
                END IF;
                INSERT INTO public.curriculum_choice_subjects VALUES(p_tenant,option_id,subject_id);
            END LOOP;
        END LOOP;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data)
    VALUES(p_actor,p_tenant,'academic.choice_group.'||CASE WHEN p_delete THEN 'delete' ELSE 'save' END,
        'curriculum_choice_groups',group_id::text,jsonb_build_object('before',previous_row,'after',p_payload));
    RETURN jsonb_build_object('choice_group_id',group_id,'institution_id',p_tenant);
END;
$$;

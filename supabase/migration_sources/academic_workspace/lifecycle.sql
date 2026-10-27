CREATE FUNCTION public.validate_academic_structure_lifecycle() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item jsonb:=to_jsonb(NEW); parent_status text; mapping record;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||NEW.institution_id::text,0));
    -- Before triggers cannot read a stored generated column's value.
    IF TG_TABLE_NAME='admission_cohorts' THEN
        item:=item||jsonb_build_object('is_active',NEW.status='active');
    END IF;
    IF item ? 'name' THEN item:=item||jsonb_build_object('name',btrim(item->>'name')); END IF;
    IF item ? 'code' THEN item:=item||jsonb_build_object('code',btrim(item->>'code')); END IF;
    IF item ? 'version' THEN item:=item||jsonb_build_object('version',btrim(item->>'version')); END IF;
    IF TG_TABLE_NAME='curriculum_subjects' THEN
        SELECT status INTO parent_status FROM public.curriculum_versions
          WHERE curriculum_version_id=NEW.curriculum_version_id AND institution_id=NEW.institution_id;
        IF parent_status IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'Published curriculum mappings are immutable' USING ERRCODE='23514';
        END IF;
    END IF;
    IF TG_TABLE_NAME='curriculum_versions' THEN
        IF TG_OP='INSERT' AND NEW.status<>'draft' THEN
            RAISE EXCEPTION 'Create a draft before publishing' USING ERRCODE='23514';
        END IF;
        IF TG_OP='UPDATE' THEN
            IF OLD.status<>'draft' AND (
                (to_jsonb(OLD)-ARRAY['status','is_active','updated_at']) IS DISTINCT FROM
                (item-ARRAY['status','is_active','updated_at'])
                OR NEW.status='draft' OR (OLD.status='archived' AND NEW.status<>'archived')) THEN
                RAISE EXCEPTION 'Published curriculum versions are immutable' USING ERRCODE='23514';
            END IF;
            IF OLD.status='draft' AND NEW.status='archived' THEN
                RAISE EXCEPTION 'Only published curricula can be archived' USING ERRCODE='23514';
            END IF;
            IF OLD.status='draft' AND NEW.status='published' THEN
                IF NOT NEW.is_active OR NOT EXISTS(SELECT 1 FROM public.curriculum_subjects
                    WHERE curriculum_version_id=NEW.curriculum_version_id AND is_active) THEN
                    RAISE EXCEPTION 'An active mapped subject is required before publication' USING ERRCODE='23514';
                END IF;
                FOR mapping IN SELECT curriculum_subject_id FROM public.curriculum_subjects
                    WHERE curriculum_version_id=NEW.curriculum_version_id AND is_active LOOP
                    PERFORM public.academic_structure_parent('curriculum_subjects',mapping.curriculum_subject_id,NEW.institution_id);
                END LOOP;
                item:=item||jsonb_build_object('published_at',now());
            END IF;
        END IF;
    END IF;
    item:=item||jsonb_build_object('updated_at',now());
    -- Exclude generated cohort field when rebuilding NEW.
    IF TG_TABLE_NAME='admission_cohorts' THEN item:=item-'is_active'; END IF;
    NEW:=jsonb_populate_record(NEW,item);
    RETURN NEW;
END;
$$;

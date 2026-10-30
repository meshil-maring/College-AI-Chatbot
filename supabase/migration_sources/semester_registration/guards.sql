CREATE FUNCTION public.guard_semester_registration_structure() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE tenant uuid:=NEW.institution_id; group_id uuid; used_count bigint;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||tenant::text,0));
    IF TG_TABLE_NAME='curriculum_subjects' THEN
        IF (NOT NEW.is_active OR NEW.is_required) AND EXISTS(
            SELECT 1 FROM public.curriculum_choice_subjects WHERE curriculum_subject_id=NEW.curriculum_subject_id
        ) THEN
            RAISE EXCEPTION 'Remove this subject from draft options before changing its status' USING ERRCODE='23514';
        END IF;
    ELSIF TG_TABLE_NAME='curriculum_versions' THEN
        IF OLD.status='draft' AND NEW.status='published' THEN
            FOR group_id IN SELECT choice_group_id FROM public.curriculum_choice_groups
                WHERE curriculum_version_id=NEW.curriculum_version_id LOOP
                IF (SELECT count(*) FROM public.curriculum_choice_options WHERE choice_group_id=group_id)<2
                   OR EXISTS(SELECT 1 FROM public.curriculum_choice_options co
                       WHERE co.choice_group_id=group_id AND NOT EXISTS(
                           SELECT 1 FROM public.curriculum_choice_subjects cs WHERE cs.choice_option_id=co.choice_option_id
                       )) THEN
                    RAISE EXCEPTION 'Complete every subject option before publishing' USING ERRCODE='23514';
                END IF;
            END LOOP;
        END IF;
    ELSIF TG_TABLE_NAME='academic_offerings' THEN
        SELECT count(*) INTO used_count FROM public.student_offering_enrollments
        WHERE academic_offering_id=NEW.academic_offering_id;
        IF used_count>0 AND (NOT NEW.is_active OR (NEW.capacity IS NOT NULL AND NEW.capacity<used_count)) THEN
            RAISE EXCEPTION 'Offering has registered students' USING ERRCODE='23514';
        END IF;
    ELSIF TG_TABLE_NAME='academic_sections' THEN
        SELECT count(*) INTO used_count FROM public.student_semester_registrations
        WHERE academic_section_id=NEW.academic_section_id;
        IF used_count>0 AND (NOT NEW.is_active OR (NEW.capacity IS NOT NULL AND NEW.capacity<used_count)) THEN
            RAISE EXCEPTION 'Section has assigned students' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

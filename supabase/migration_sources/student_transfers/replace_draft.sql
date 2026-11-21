-- The 20261107 draft created transfer tables that no code path could write to:
-- every insert referenced columns those tables never defined. Remove them only
-- while they are still empty so that no recorded data can be lost silently.
DO $$
DECLARE relation_name text; has_rows boolean;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['transfer_request_actions', 'transfer_requests',
        'student_academic_placements', 'subject_equivalencies', 'institution_transfer_settings'] LOOP
        IF to_regclass(format('public.%I', relation_name)) IS NOT NULL THEN
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM public.%I)', relation_name) INTO has_rows;
            IF has_rows THEN
                RAISE EXCEPTION 'Draft transfer table public.% contains rows; inspect it before migrating',
                    relation_name;
            END IF;
            EXECUTE format('DROP TABLE public.%I', relation_name);
        END IF;
    END LOOP;
END;
$$;

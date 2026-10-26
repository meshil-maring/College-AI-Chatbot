DO $$
BEGIN
    PERFORM academic_setup_check.verify_decommission_retained();
    IF EXISTS (SELECT 1 FROM academic_setup_check.retired_tables
        WHERE to_regclass(format('public.%I',name)) IS NOT NULL) THEN
        RAISE EXCEPTION 'Retired academic tables remain';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
        AND table_name='students' AND column_name IN ('program_id','academic_year_id')) THEN
        RAISE EXCEPTION 'Retired student academic references remain';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.students
        WHERE student_id=(SELECT value FROM academic_decommission_fixture.ids WHERE name='profile')
        AND register_number='DC-PRESERVED' AND university_roll_number='DC-ROLL'
        AND approval_status='approved' AND is_active) THEN
        RAISE EXCEPTION 'Synthetic canonical student identity was not retained';
    END IF;
END $$;

DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['department_heads', 'student_transfer_requests',
        'student_transfer_events'] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role',
            relation_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', relation_name);
    END LOOP;
END;
$$;

REVOKE ALL ON FUNCTION
    public.assert_transfer_backend(),
    public.transfer_admin_allowed(uuid, uuid, text),
    public.transfer_is_active_faculty(uuid, uuid),
    public.transfer_hod_departments(uuid, uuid),
    public.assert_transfer_student(uuid, uuid, text),
    public.transfer_current_registration(uuid, uuid),
    public.transfer_section_json(uuid, uuid),
    public.transfer_target_type(uuid, uuid, uuid),
    public.transfer_section_has_seat(uuid),
    public.transfer_requests_json(uuid, uuid, uuid[], boolean),
    public.read_student_transfers(uuid, uuid),
    public.submit_student_transfer(uuid, uuid, uuid, text),
    public.cancel_student_transfer(uuid, uuid, uuid),
    public.read_transfer_reviews(uuid, uuid, boolean),
    public.decide_student_transfer(uuid, uuid, uuid, text, text),
    public.read_department_heads(uuid, uuid),
    public.assign_department_head(uuid, uuid, uuid, uuid)
FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION
    public.read_student_transfers(uuid, uuid),
    public.submit_student_transfer(uuid, uuid, uuid, text),
    public.cancel_student_transfer(uuid, uuid, uuid),
    public.read_transfer_reviews(uuid, uuid, boolean),
    public.decide_student_transfer(uuid, uuid, uuid, text, text),
    public.read_department_heads(uuid, uuid),
    public.assign_department_head(uuid, uuid, uuid, uuid)
TO service_role;

NOTIFY pgrst, 'reload schema';

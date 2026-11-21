REVOKE ALL ON FUNCTION
    public.transfer_stage_matches(uuid, uuid),
    public.direct_transfer_student(uuid, uuid, uuid, uuid, text, boolean)
FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION
    public.direct_transfer_student(uuid, uuid, uuid, uuid, text, boolean)
TO service_role;

NOTIFY pgrst, 'reload schema';

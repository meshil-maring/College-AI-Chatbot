REVOKE ALL ON FUNCTION
    public.transfer_apply(uuid, uuid, uuid, text, text),
    public.transfer_direct_role(uuid, uuid),
    public.read_direct_transfer_students(uuid, uuid),
    public.read_direct_transfer_options(uuid, uuid, uuid),
    public.direct_transfer_student(uuid, uuid, uuid, uuid, text)
FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION
    public.read_direct_transfer_students(uuid, uuid),
    public.read_direct_transfer_options(uuid, uuid, uuid),
    public.direct_transfer_student(uuid, uuid, uuid, uuid, text)
TO service_role;

NOTIFY pgrst, 'reload schema';

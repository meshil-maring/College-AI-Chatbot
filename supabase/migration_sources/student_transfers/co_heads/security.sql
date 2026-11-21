-- Helpers stay internal; only the backend service role may run the commands.
REVOKE ALL ON FUNCTION
    public.department_head_lock(uuid, uuid, uuid),
    public.department_head_ids(uuid, uuid),
    public.read_department_heads(uuid, uuid),
    public.add_department_head(uuid, uuid, uuid, uuid),
    public.end_department_head(uuid, uuid, uuid, uuid),
    public.assign_department_head(uuid, uuid, uuid, uuid)
FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION
    public.read_department_heads(uuid, uuid),
    public.add_department_head(uuid, uuid, uuid, uuid),
    public.end_department_head(uuid, uuid, uuid, uuid),
    public.assign_department_head(uuid, uuid, uuid, uuid)
TO service_role;

NOTIFY pgrst, 'reload schema';

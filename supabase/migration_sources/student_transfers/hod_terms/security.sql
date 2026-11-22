-- Helpers stay internal; only the backend service role may run the commands.
REVOKE ALL ON FUNCTION
    public.department_head_today(),
    public.department_head_in_effect(timestamptz, date),
    public.department_head_guard(),
    public.add_department_head(uuid, uuid, uuid, uuid, date, date),
    public.set_department_head_term(uuid, uuid, uuid, uuid, date, date),
    public.set_department_head_policy(uuid, uuid, boolean)
FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION
    public.add_department_head(uuid, uuid, uuid, uuid, date, date),
    public.set_department_head_term(uuid, uuid, uuid, uuid, date, date),
    public.set_department_head_policy(uuid, uuid, boolean)
TO service_role;

NOTIFY pgrst, 'reload schema';

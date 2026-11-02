REVOKE ALL ON FUNCTION public.update_admin_student_profile(uuid,uuid,uuid,text,text,text,uuid),
    public.set_admin_student_active(uuid,uuid,uuid,boolean),
    public.delete_unused_admin_student(uuid,uuid,uuid)
    FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.update_admin_student_profile(uuid,uuid,uuid,text,text,text,uuid),
    public.set_admin_student_active(uuid,uuid,uuid,boolean),
    public.delete_unused_admin_student(uuid,uuid,uuid)
    TO service_role;
NOTIFY pgrst,'reload schema';

REVOKE ALL ON FUNCTION public.read_admin_student_directory(uuid,uuid,text,text,uuid,integer,integer)
    FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.read_admin_student_directory(uuid,uuid,text,text,uuid,integer,integer)
    TO service_role;
NOTIFY pgrst,'reload schema';

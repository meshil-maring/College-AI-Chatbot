REVOKE ALL ON FUNCTION public.update_student_onboarding_invitation(
    uuid,uuid,uuid,text,text,text,uuid
),public.cancel_student_onboarding_invitation(uuid,uuid,uuid)
FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.update_student_onboarding_invitation(
    uuid,uuid,uuid,text,text,text,uuid
),public.cancel_student_onboarding_invitation(uuid,uuid,uuid)
TO service_role;
NOTIFY pgrst,'reload schema';

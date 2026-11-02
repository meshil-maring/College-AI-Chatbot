REVOKE ALL ON FUNCTION public.update_student_onboarding_invitation(
    uuid,uuid,uuid,text,text,text,text,uuid,text,timestamptz
),public.cancel_student_onboarding_invitation(uuid,uuid,uuid),
public.claim_student_onboarding_setup(uuid,text),
public.release_student_onboarding_setup(uuid,text)
FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.update_student_onboarding_invitation(
    uuid,uuid,uuid,text,text,text,text,uuid,text,timestamptz
),public.cancel_student_onboarding_invitation(uuid,uuid,uuid),
public.claim_student_onboarding_setup(uuid,text),
public.release_student_onboarding_setup(uuid,text)
TO service_role;
NOTIFY pgrst,'reload schema';

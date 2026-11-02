ALTER TABLE public.student_onboarding_invitations OWNER TO postgres;
ALTER TABLE public.student_onboarding_invitations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.student_onboarding_invitations FROM PUBLIC,anon,authenticated,service_role;

REVOKE ALL ON FUNCTION public.create_student_onboarding_invitation(uuid,uuid,text,text,text,text,uuid,text,timestamptz),
    public.read_student_onboarding_invitations(uuid,uuid),
    public.reassign_student_onboarding_section(uuid,uuid,uuid,uuid),
    public.resend_student_onboarding_invitation(uuid,uuid,uuid,text,timestamptz),
    public.record_student_onboarding_delivery(uuid,uuid,uuid,text,text),
    public.record_student_onboarding_auth_user(uuid,text,uuid),
    public.inspect_student_onboarding_invitation(text),
    public.complete_student_onboarding_invitation(uuid,text,uuid)
    FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.create_student_onboarding_invitation(uuid,uuid,text,text,text,text,uuid,text,timestamptz),
    public.read_student_onboarding_invitations(uuid,uuid),
    public.reassign_student_onboarding_section(uuid,uuid,uuid,uuid),
    public.resend_student_onboarding_invitation(uuid,uuid,uuid,text,timestamptz),
    public.record_student_onboarding_delivery(uuid,uuid,uuid,text,text),
    public.record_student_onboarding_auth_user(uuid,text,uuid),
    public.inspect_student_onboarding_invitation(text),
    public.complete_student_onboarding_invitation(uuid,text,uuid) TO service_role;
NOTIFY pgrst,'reload schema';

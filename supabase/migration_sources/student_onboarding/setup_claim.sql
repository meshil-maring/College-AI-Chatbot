CREATE FUNCTION public.claim_student_onboarding_setup(
    p_invitation uuid,p_token_hash text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE claimed boolean;
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    UPDATE public.student_onboarding_invitations
    SET setup_started_at=coalesce(setup_started_at,clock_timestamp()),updated_at=now()
    WHERE invitation_id=p_invitation AND token_hash=p_token_hash
        AND status='pending' AND expires_at>clock_timestamp()
    RETURNING true INTO claimed;
    RETURN coalesce(claimed,false);
END;
$$;

CREATE FUNCTION public.release_student_onboarding_setup(
    p_invitation uuid,p_token_hash text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE released boolean;
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    UPDATE public.student_onboarding_invitations invitation
    SET setup_started_at=NULL,updated_at=now()
    WHERE invitation_id=p_invitation AND token_hash=p_token_hash
        AND status='pending' AND provisioned_auth_user_id IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM auth.users auth_user
            WHERE auth_user.raw_app_meta_data->>'student_onboarding_invitation_id'
                =invitation.invitation_id::text
        )
    RETURNING true INTO released;
    RETURN coalesce(released,false);
END;
$$;

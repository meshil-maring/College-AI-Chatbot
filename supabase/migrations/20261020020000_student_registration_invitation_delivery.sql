-- Require email for new registrations while preserving historical records.
ALTER TABLE public.student_registrations ADD CONSTRAINT student_registration_email_required
    CHECK (email IS NOT NULL AND length(btrim(email)) BETWEEN 3 AND 128) NOT VALID;

CREATE TABLE public.student_registration_invitations (
    registration_id uuid PRIMARY KEY REFERENCES public.student_registrations(registration_id) ON DELETE RESTRICT,
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    requested_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    status text NOT NULL CHECK (status IN ('sending', 'sent', 'failed', 'captured')),
    attempt_id uuid NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    requested_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    provider text
);
ALTER TABLE public.student_registration_invitations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.student_registration_invitations FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.student_registration_invitations TO service_role;

CREATE FUNCTION public.claim_student_registration_invitation(p_tenant uuid, p_registration_id uuid, p_actor uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE delivery public.student_registration_invitations%ROWTYPE;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.student_registrations r
                   WHERE r.registration_id = p_registration_id AND r.institution_id = p_tenant
                     AND r.email IS NOT NULL AND length(btrim(r.email)) > 0) THEN
        RAISE EXCEPTION 'Registration unavailable' USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.student_registration_invitations
        (registration_id, institution_id, requested_by, status, attempt_id)
    VALUES (p_registration_id, p_tenant, p_actor, 'failed', gen_random_uuid())
    ON CONFLICT (registration_id) DO NOTHING;
    SELECT * INTO STRICT delivery FROM public.student_registration_invitations
        WHERE registration_id = p_registration_id AND institution_id = p_tenant FOR UPDATE;
    IF delivery.status = 'sent' THEN
        RETURN jsonb_build_object('claimed', false, 'status', 'sent');
    END IF;
    -- A request interrupted during delivery is intentionally not resent automatically:
    -- its provider outcome may be unknown. This prevents duplicate invitations.
    IF delivery.status = 'sending' THEN
        RETURN jsonb_build_object('claimed', false, 'status', 'sending');
    END IF;
    UPDATE public.student_registration_invitations
       SET status = 'sending', attempt_id = gen_random_uuid(), requested_by = p_actor,
           requested_at = now(), completed_at = NULL, attempt_count = attempt_count + 1
     WHERE registration_id = p_registration_id RETURNING * INTO delivery;
    RETURN jsonb_build_object('claimed', true, 'status', 'sending', 'attempt_id', delivery.attempt_id);
END;
$$;

CREATE FUNCTION public.complete_student_registration_invitation(p_tenant uuid, p_registration_id uuid,
    p_attempt_id uuid, p_status text, p_provider text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF p_status NOT IN ('sent', 'failed', 'captured') THEN
        RAISE EXCEPTION 'Invalid delivery outcome' USING ERRCODE = '23514';
    END IF;
    UPDATE public.student_registration_invitations
       SET status = p_status, provider = left(p_provider, 64), completed_at = now()
     WHERE registration_id = p_registration_id AND institution_id = p_tenant
       AND attempt_id = p_attempt_id AND status = 'sending';
    RETURN FOUND;
END;
$$;
REVOKE ALL ON FUNCTION public.claim_student_registration_invitation(uuid, uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_student_registration_invitation(uuid, uuid, uuid, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_student_registration_invitation(uuid, uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_student_registration_invitation(uuid, uuid, uuid, text, text) TO service_role;
NOTIFY pgrst, 'reload schema';

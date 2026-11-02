CREATE TABLE public.student_onboarding_invitations (
    invitation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    email text NOT NULL,
    student_name text NOT NULL CHECK (length(btrim(student_name)) BETWEEN 1 AND 200),
    register_number text NOT NULL CHECK (length(btrim(register_number)) BETWEEN 1 AND 128),
    university_roll_number text CHECK (
        university_roll_number IS NULL OR length(btrim(university_roll_number)) BETWEEN 1 AND 128
    ),
    academic_section_id uuid NOT NULL,
    token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'cancelled')),
    expires_at timestamptz NOT NULL,
    created_by uuid NOT NULL REFERENCES public.users(id),
    provisioned_auth_user_id uuid REFERENCES auth.users(id),
    accepted_auth_user_id uuid REFERENCES auth.users(id),
    accepted_user_id uuid REFERENCES public.users(id),
    student_id uuid REFERENCES public.students(student_id),
    email_delivery_status text NOT NULL DEFAULT 'pending'
        CHECK (email_delivery_status IN ('pending', 'sent', 'failed')),
    email_delivery_attempts integer NOT NULL DEFAULT 0 CHECK (email_delivery_attempts >= 0),
    resend_window_started_at timestamptz,
    resend_window_count integer NOT NULL DEFAULT 0 CHECK (resend_window_count BETWEEN 0 AND 3),
    last_sent_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (invitation_id, institution_id),
    FOREIGN KEY (academic_section_id, institution_id)
        REFERENCES public.academic_sections(academic_section_id, institution_id),
    CHECK (
        (status = 'accepted' AND accepted_auth_user_id IS NOT NULL AND accepted_user_id IS NOT NULL
            AND student_id IS NOT NULL)
        OR (status <> 'accepted' AND accepted_auth_user_id IS NULL AND accepted_user_id IS NULL
            AND student_id IS NULL)
    )
);
CREATE UNIQUE INDEX student_onboarding_pending_email
    ON public.student_onboarding_invitations(institution_id, lower(email)) WHERE status = 'pending';
CREATE UNIQUE INDEX student_onboarding_pending_register
    ON public.student_onboarding_invitations(institution_id, lower(btrim(register_number)))
    WHERE status = 'pending';
CREATE UNIQUE INDEX student_onboarding_pending_roll
    ON public.student_onboarding_invitations(institution_id, lower(btrim(university_roll_number)))
    WHERE status = 'pending' AND university_roll_number IS NOT NULL;
CREATE INDEX student_onboarding_invitations_created
    ON public.student_onboarding_invitations(institution_id, created_at DESC);

\set ON_ERROR_STOP on

-- Local-only Phase 7.18 reconciliation validation. All fixtures roll back.
BEGIN;

INSERT INTO auth.users (id)
VALUES ('71800000-0000-0000-0000-000000000001');
INSERT INTO public.users (id, auth_user_id, email, first_name, last_name)
VALUES (
    '71800000-0000-0000-0000-000000000002',
    '71800000-0000-0000-0000-000000000001',
    'phase718-actor@example.test', 'Phase', 'Eighteen'
);
INSERT INTO public.organizations (
    organization_id, name, organization_code, official_email,
    contact_information, status
) VALUES (
    '71800000-0000-0000-0000-000000000003',
    'Phase 718 Local Organization', 'PHASE718',
    'phase718-org@example.test', 'local validation only', 'active'
);
INSERT INTO public.institutions (
    institution_id, organization_id, name, code, status, is_active
) VALUES
    (
        '71800000-0000-0000-0000-000000000004',
        '71800000-0000-0000-0000-000000000003',
        'Phase 718 University A', 'P718A', 'active', true
    ),
    (
        '71800000-0000-0000-0000-000000000005',
        '71800000-0000-0000-0000-000000000003',
        'Phase 718 University B', 'P718B', 'active', true
    );

DO $$
DECLARE
    v_a jsonb;
    v_b jsonb;
    v_rotated jsonb;
    v_claim public.email_outbox%ROWTYPE;
    v_result jsonb;
    v_status text;
BEGIN
    v_a := public.phase717_create_invitation_with_outbox(
        '71800000-0000-0000-0000-000000000004',
        'phase718-a@example.test', repeat('a', 64), now() + interval '1 day',
        '71800000-0000-0000-0000-000000000002', repeat('x', 120)
    );
    SELECT * INTO v_claim FROM public.phase717_claim_email_outbox(1, 120, 3);
    IF NOT public.phase717_complete_email_outbox(
        v_claim.id, 1, 'sent', 'mailgun', 'message-a@mg.example.test', NULL, NULL
    ) THEN
        RAISE EXCEPTION 'failed to seed Mailgun submission A';
    END IF;

    v_b := public.phase717_create_invitation_with_outbox(
        '71800000-0000-0000-0000-000000000005',
        'phase718-b@example.test', repeat('b', 64), now() + interval '1 day',
        '71800000-0000-0000-0000-000000000002', repeat('y', 120)
    );
    SELECT * INTO v_claim FROM public.phase717_claim_email_outbox(1, 120, 3);
    IF NOT public.phase717_complete_email_outbox(
        v_claim.id, 1, 'sent', 'mailgun', 'message-b@mg.example.test', NULL, NULL
    ) THEN
        RAISE EXCEPTION 'failed to seed Mailgun submission B';
    END IF;

    v_result := public.phase718_reconcile_mailgun_event(
        repeat('1', 64), repeat('a', 64), 'event-delivered-a',
        'message-a@mg.example.test', 'delivered', now()
    );
    IF v_result->>'result' <> 'applied' OR (v_result->>'state_changed')::boolean IS NOT TRUE THEN
        RAISE EXCEPTION 'delivery event was not applied: %', v_result;
    END IF;
    SELECT status INTO v_status FROM public.email_outbox
    WHERE provider_message_id = 'message-a@mg.example.test';
    IF v_status <> 'delivered' THEN
        RAISE EXCEPTION 'message A did not become delivered';
    END IF;
    SELECT status INTO v_status FROM public.email_outbox
    WHERE provider_message_id = 'message-b@mg.example.test';
    IF v_status <> 'sent' THEN
        RAISE EXCEPTION 'cross-tenant message B was modified';
    END IF;

    -- Both the stable event key and the signing token digest independently
    -- prevent replays.
    v_result := public.phase718_reconcile_mailgun_event(
        repeat('1', 64), repeat('a', 64), 'event-delivered-a',
        'message-a@mg.example.test', 'delivered', now()
    );
    IF v_result->>'result' <> 'duplicate' THEN
        RAISE EXCEPTION 'duplicate event was not deduplicated';
    END IF;
    v_result := public.phase718_reconcile_mailgun_event(
        repeat('2', 64), repeat('a', 64), 'event-token-replay',
        'message-a@mg.example.test', 'permanent_failure', now()
    );
    IF v_result->>'result' <> 'duplicate' THEN
        RAISE EXCEPTION 'replayed signing token was not deduplicated';
    END IF;

    v_result := public.phase718_reconcile_mailgun_event(
        repeat('3', 64), repeat('b', 64), 'event-bounce-a',
        'message-a@mg.example.test', 'permanent_failure', now()
    );
    IF v_result->>'result' <> 'applied' THEN
        RAISE EXCEPTION 'permanent failure was not applied';
    END IF;
    v_result := public.phase718_reconcile_mailgun_event(
        repeat('4', 64), repeat('c', 64), 'event-late-delivery-a',
        'message-a@mg.example.test', 'delivered', now()
    );
    IF v_result->>'result' <> 'no_state_change' THEN
        RAISE EXCEPTION 'late delivery resurrected a permanent failure';
    END IF;

    v_result := public.phase718_reconcile_mailgun_event(
        repeat('5', 64), repeat('d', 64), 'event-unknown',
        'unknown@mg.example.test', 'delivered', now()
    );
    IF v_result->>'result' <> 'unknown_message' THEN
        RAISE EXCEPTION 'unknown provider message was not isolated';
    END IF;

    -- A resend creates a higher durable delivery sequence. A late event for
    -- the old message may update old history but cannot overwrite the current
    -- invitation projection.
    SELECT to_jsonb(i) INTO v_rotated
    FROM public.platform_admin_invitations AS i
    WHERE i.invitation_id = (v_a->>'invitation_id')::uuid;
    v_rotated := public.phase717_rotate_invitation_with_outbox(
        (v_a->>'invitation_id')::uuid, repeat('c', 64), now() + interval '1 day',
        (v_rotated->>'updated_at')::timestamptz, repeat('z', 120), 120
    );
    IF v_rotated IS NULL THEN
        RAISE EXCEPTION 'resend generation was not created';
    END IF;
    v_result := public.phase718_reconcile_mailgun_event(
        repeat('6', 64), repeat('e', 64), 'event-old-complaint-a',
        'message-a@mg.example.test', 'complained', now()
    );
    IF v_result->>'result' <> 'stale_generation' THEN
        RAISE EXCEPTION 'old delivery generation was not isolated';
    END IF;
    SELECT email_delivery_status INTO v_status
    FROM public.platform_admin_invitations
    WHERE invitation_id = (v_a->>'invitation_id')::uuid;
    IF v_status <> 'pending' THEN
        RAISE EXCEPTION 'old event overwrote current resend state';
    END IF;
END;
$$;

ROLLBACK;
SELECT 'phase718 local Mailgun webhook validation passed' AS result;


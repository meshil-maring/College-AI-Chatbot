\set ON_ERROR_STOP on

-- Local-only Phase 7.17 database behaviour check. Every fixture and state
-- transition is rolled back; this script never targets a linked project.
BEGIN;

INSERT INTO auth.users (id)
VALUES ('71700000-0000-0000-0000-000000000001');
INSERT INTO public.users (id, auth_user_id, email, first_name, last_name)
VALUES (
    '71700000-0000-0000-0000-000000000002',
    '71700000-0000-0000-0000-000000000001',
    'phase717-actor@example.test', 'Phase', 'Seventeen'
);
INSERT INTO public.organizations (
    organization_id, name, organization_code, official_email,
    contact_information, status
) VALUES (
    '71700000-0000-0000-0000-000000000003',
    'Phase 717 Local Organization', 'PHASE717',
    'phase717-org@example.test', 'local validation only', 'active'
);
INSERT INTO public.institutions (
    institution_id, organization_id, name, code, status, is_active
) VALUES (
    '71700000-0000-0000-0000-000000000004',
    '71700000-0000-0000-0000-000000000003',
    'Phase 717 Local University', 'P717', 'active', true
);

DO $$
DECLARE
    v_created jsonb;
    v_rotated jsonb;
    v_claim public.email_outbox%ROWTYPE;
    v_count integer;
    v_completed boolean;
BEGIN
    v_created := public.phase717_create_invitation_with_outbox(
        '71700000-0000-0000-0000-000000000004',
        'phase717-invitee@example.test',
        repeat('a', 64),
        now() + interval '1 day',
        '71700000-0000-0000-0000-000000000002',
        repeat('x', 120)
    );
    IF v_created->>'invitation_id' IS NULL
       OR v_created->>'email_outbox_id' IS NULL THEN
        RAISE EXCEPTION 'atomic invitation/outbox creation failed';
    END IF;
    SELECT count(*) INTO v_count FROM public.email_outbox
    WHERE aggregate_id = (v_created->>'invitation_id')::uuid;
    IF v_count <> 1 THEN
        RAISE EXCEPTION 'expected exactly one initial outbox row, got %', v_count;
    END IF;

    -- Resend atomically cancels the old pending job and creates one new job.
    v_rotated := public.phase717_rotate_invitation_with_outbox(
        (v_created->>'invitation_id')::uuid,
        repeat('b', 64),
        now() + interval '1 day',
        (v_created->>'updated_at')::timestamptz,
        repeat('y', 120),
        120
    );
    IF v_rotated IS NULL THEN
        RAISE EXCEPTION 'pending resend did not rotate';
    END IF;
    SELECT count(*) INTO v_count FROM public.email_outbox
    WHERE aggregate_id = (v_created->>'invitation_id')::uuid
      AND status = 'cancelled';
    IF v_count <> 1 THEN
        RAISE EXCEPTION 'resend did not cancel old pending job';
    END IF;

    SELECT * INTO v_claim
    FROM public.phase717_claim_email_outbox(1, 120, 3);
    IF v_claim.id IS NULL OR v_claim.attempt_count <> 1 THEN
        RAISE EXCEPTION 'first worker did not claim the current job';
    END IF;
    SELECT count(*) INTO v_count
    FROM public.phase717_claim_email_outbox(1, 120, 3);
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'second worker claimed an already leased job';
    END IF;

    -- A resend cannot invalidate a token while a non-stale provider call owns
    -- the lease. This serializes the resend/provider race.
    v_rotated := public.phase717_rotate_invitation_with_outbox(
        (v_created->>'invitation_id')::uuid,
        repeat('c', 64),
        now() + interval '1 day',
        (v_rotated->>'updated_at')::timestamptz,
        repeat('z', 120),
        120
    );
    IF v_rotated IS NOT NULL THEN
        RAISE EXCEPTION 'resend raced an active worker lease';
    END IF;

    -- Simulate a crash, then prove the stale lease is reclaimed as attempt 2.
    UPDATE public.email_outbox
    SET locked_at = now() - interval '121 seconds'
    WHERE id = v_claim.id;
    SELECT * INTO v_claim
    FROM public.phase717_claim_email_outbox(1, 120, 3);
    IF v_claim.id IS NULL OR v_claim.attempt_count <> 2 THEN
        RAISE EXCEPTION 'stale worker lease was not recovered';
    END IF;

    v_completed := public.phase717_complete_email_outbox(
        v_claim.id, 2, 'sent', 'local-test', 'provider-message-717', NULL, NULL
    );
    IF NOT v_completed THEN
        RAISE EXCEPTION 'claimed job did not settle';
    END IF;
    SELECT count(*) INTO v_count FROM public.email_delivery_attempts
    WHERE outbox_id = v_claim.id;
    IF v_count <> 2 THEN
        RAISE EXCEPTION 'attempt history was not retained';
    END IF;
END;
$$;

ROLLBACK;
SELECT 'phase717 local outbox validation passed' AS result;

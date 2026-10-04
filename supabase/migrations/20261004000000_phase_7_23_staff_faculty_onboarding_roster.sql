-- Phase 7.23 - institution Staff/Faculty onboarding and roster prerequisites.
--
-- This deliberately extends the Phase 7.14-7.18 invitation table/outbox. It
-- does not introduce a second token, invitation, identity, or delivery system.

ALTER TABLE "public"."platform_admin_invitations"
    DROP CONSTRAINT IF EXISTS "platform_admin_invitations_role_name_check";

ALTER TABLE "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_role_name_check"
    CHECK ("role_name" = ANY (ARRAY['admin'::text, 'staff'::text, 'faculty'::text]));

COMMENT ON TABLE "public"."platform_admin_invitations" IS
    'Generic institution-role invitations. Server-owned role_name is limited to admin, staff, or faculty; raw tokens are never stored.';

-- Overload (rather than replace) the Phase 7.17 six-argument function so old
-- deployments/callers remain compatible. University Admin code calls this
-- overload with a server-derived staff/faculty role. The function and CHECK
-- constraint independently reject super_admin/platform scope.
CREATE OR REPLACE FUNCTION "public"."phase717_create_invitation_with_outbox"(
    "p_institution_id" uuid,
    "p_email" text,
    "p_token_hash" text,
    "p_expires_at" timestamp with time zone,
    "p_created_by" uuid,
    "p_protected_token" text,
    "p_role_name" text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    IF p_role_name NOT IN ('admin', 'staff', 'faculty') THEN
        RAISE EXCEPTION 'unsupported institution invitation role'
            USING ERRCODE = '22023';
    END IF;

    UPDATE "public"."platform_admin_invitations"
    SET "status" = 'expired'::text, "updated_at" = now()
    WHERE "institution_id" = p_institution_id
      AND lower("email") = lower(btrim(p_email))
      AND "status" = 'invited'::text
      AND "expires_at" <= now();

    INSERT INTO "public"."platform_admin_invitations" (
        "institution_id", "email", "token_hash", "role_name", "status",
        "expires_at", "created_by", "email_delivery_status"
    ) VALUES (
        p_institution_id, lower(btrim(p_email)), p_token_hash, p_role_name,
        'invited'::text, p_expires_at, p_created_by, 'pending'::text
    ) RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (v_invitation."invitation_id", p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

REVOKE ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"(
    uuid, text, text, timestamp with time zone, uuid, text, text
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION "public"."phase717_create_invitation_with_outbox"(
    uuid, text, text, timestamp with time zone, uuid, text, text
) TO service_role;

CREATE OR REPLACE FUNCTION "public"."phase717_resolve_email_outbox_context"(
    "p_outbox_id" uuid,
    "p_token_hash" text
) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT CASE
        WHEN o."status" = 'processing'::text
         AND i."status" = 'invited'::text
         AND i."expires_at" > now()
         AND i."token_hash" = p_token_hash
        THEN jsonb_build_object(
            'invitation_id', i."invitation_id",
            'recipient', i."email",
            'institution_name', n."name",
            'expires_at', i."expires_at",
            'role_name', i."role_name"
        )
        ELSE NULL
    END
    FROM "public"."email_outbox" AS o
    JOIN "public"."platform_admin_invitations" AS i
      ON i."invitation_id" = o."aggregate_id"
    JOIN "public"."institutions" AS n
      ON n."institution_id" = i."institution_id"
    WHERE o."id" = p_outbox_id;
$$;

-- One transaction is the approval state machine: lock the request, re-check
-- tenant/role/applicant/institution state, create the existing invitation +
-- outbox pair, then mark the request approved. Concurrent approve/approve and
-- approve/reject calls therefore have exactly one logical winner.
CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_with_invitation"(
    "p_request_id" uuid,
    "p_institution_id" uuid,
    "p_decided_by" uuid,
    "p_reason" text,
    "p_token_hash" text,
    "p_expires_at" timestamp with time zone,
    "p_protected_token" text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_request "public"."institution_membership_requests"%ROWTYPE;
    v_invitation jsonb;
BEGIN
    SELECT * INTO v_request
    FROM "public"."institution_membership_requests"
    WHERE "request_id" = p_request_id
      AND "institution_id" = p_institution_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('not_found', true);
    END IF;
    IF v_request."status" = 'approved'::text THEN
        RETURN jsonb_build_object('already_applied', true);
    END IF;
    IF v_request."status" <> 'pending'::text THEN
        RETURN jsonb_build_object('conflict', true);
    END IF;
    IF v_request."requested_role" NOT IN ('staff', 'faculty') THEN
        RETURN jsonb_build_object('invalid_role', true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "public"."institutions" AS i
        WHERE i."institution_id" = p_institution_id
          AND i."status" = 'active'::text AND i."is_active" = true
          AND i."organization_id" = v_request."organization_id"
    ) OR NOT EXISTS (
        SELECT 1 FROM "public"."users" AS u
        WHERE u."id" = v_request."user_id"
          AND lower(u."email") = lower(v_request."official_email")
          AND u."status" = 'active'::text
    ) THEN
        RETURN jsonb_build_object('invalid_state', true);
    END IF;

    SELECT "public"."phase717_create_invitation_with_outbox"(
        p_institution_id, v_request."official_email", p_token_hash,
        p_expires_at, p_decided_by, p_protected_token,
        v_request."requested_role"
    ) INTO v_invitation;

    UPDATE "public"."institution_membership_requests"
    SET "status" = 'approved'::text,
        "decided_by_user_id" = p_decided_by,
        "decided_at" = now(),
        "decision_reason" = p_reason,
        "updated_at" = now()
    WHERE "request_id" = p_request_id;

    RETURN v_invitation || jsonb_build_object('already_applied', false);
END;
$$;

REVOKE ALL ON FUNCTION "public"."phase723_approve_membership_with_invitation"(
    uuid, uuid, uuid, text, text, timestamp with time zone, text
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION "public"."phase723_approve_membership_with_invitation"(
    uuid, uuid, uuid, text, text, timestamp with time zone, text
) TO service_role;

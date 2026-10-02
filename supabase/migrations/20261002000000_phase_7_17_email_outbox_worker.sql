-- Phase 7.17 -- provider-neutral durable invitation-email outbox and worker.
--
-- No vendor is authorized in this repository. This migration therefore adds
-- no provider webhook schema or provider-specific objects. It implements the
-- durable, service-role-only boundary that an authorized adapter can consume.

CREATE TABLE IF NOT EXISTS "public"."email_outbox" (
    "id" uuid DEFAULT gen_random_uuid() NOT NULL,
    "message_type" text DEFAULT 'admin_invitation'::text NOT NULL,
    "aggregate_type" text DEFAULT 'platform_admin_invitation'::text NOT NULL,
    "aggregate_id" uuid NOT NULL,
    "protected_token" text,
    "status" text DEFAULT 'pending'::text NOT NULL,
    "attempt_count" integer DEFAULT 0 NOT NULL,
    "available_at" timestamp with time zone DEFAULT now() NOT NULL,
    "locked_at" timestamp with time zone,
    "sent_at" timestamp with time zone,
    "failed_at" timestamp with time zone,
    "delivery_updated_at" timestamp with time zone,
    "provider_name" text,
    "provider_message_id" text,
    "last_error_category" text,
    "created_at" timestamp with time zone DEFAULT now() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT "email_outbox_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "email_outbox_invitation_fkey" FOREIGN KEY ("aggregate_id")
        REFERENCES "public"."platform_admin_invitations" ("invitation_id"),
    CONSTRAINT "email_outbox_message_type_check"
        CHECK ("message_type" = 'admin_invitation'::text),
    CONSTRAINT "email_outbox_aggregate_type_check"
        CHECK ("aggregate_type" = 'platform_admin_invitation'::text),
    CONSTRAINT "email_outbox_status_check" CHECK ("status" = ANY (ARRAY[
        'pending'::text, 'processing'::text, 'sent'::text,
        'delivered'::text, 'bounced'::text, 'complained'::text,
        'dead_letter'::text, 'cancelled'::text
    ])),
    CONSTRAINT "email_outbox_attempt_count_check" CHECK ("attempt_count" >= 0),
    CONSTRAINT "email_outbox_protected_token_check"
        CHECK (
            ("status" IN ('pending'::text, 'processing'::text)
             AND "protected_token" IS NOT NULL
             AND length(btrim("protected_token")) >= 80)
            OR
            ("status" NOT IN ('pending'::text, 'processing'::text)
             AND "protected_token" IS NULL)
        ),
    CONSTRAINT "email_outbox_processing_lock_check" CHECK (
        ("status" = 'processing'::text AND "locked_at" IS NOT NULL)
        OR ("status" <> 'processing'::text AND "locked_at" IS NULL)
    )
);

COMMENT ON COLUMN "public"."email_outbox"."protected_token" IS
    'Authenticated ciphertext needed to render the one-time URL. Never plaintext; key remains backend-only.';

CREATE INDEX IF NOT EXISTS "email_outbox_claim_idx"
    ON "public"."email_outbox" ("available_at", "created_at")
    WHERE "status" = 'pending'::text;
CREATE INDEX IF NOT EXISTS "email_outbox_stale_lock_idx"
    ON "public"."email_outbox" ("locked_at")
    WHERE "status" = 'processing'::text;
CREATE INDEX IF NOT EXISTS "email_outbox_aggregate_idx"
    ON "public"."email_outbox" ("aggregate_id", "created_at" DESC);
CREATE UNIQUE INDEX IF NOT EXISTS "email_outbox_provider_message_idx"
    ON "public"."email_outbox" ("provider_name", "provider_message_id")
    WHERE "provider_message_id" IS NOT NULL;

CREATE TABLE IF NOT EXISTS "public"."email_delivery_attempts" (
    "id" uuid DEFAULT gen_random_uuid() NOT NULL,
    "outbox_id" uuid NOT NULL,
    "attempt_number" integer NOT NULL,
    "started_at" timestamp with time zone DEFAULT now() NOT NULL,
    "completed_at" timestamp with time zone,
    "result" text DEFAULT 'processing'::text NOT NULL,
    "failure_category" text,
    "provider_message_id" text,
    CONSTRAINT "email_delivery_attempts_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "email_delivery_attempts_outbox_fkey" FOREIGN KEY ("outbox_id")
        REFERENCES "public"."email_outbox" ("id") ON DELETE CASCADE,
    CONSTRAINT "email_delivery_attempts_number_check" CHECK ("attempt_number" > 0),
    CONSTRAINT "email_delivery_attempts_result_check" CHECK ("result" = ANY (ARRAY[
        'processing'::text, 'sent'::text, 'retry'::text,
        'dead_letter'::text, 'cancelled'::text
    ])),
    CONSTRAINT "email_delivery_attempts_outbox_number_key"
        UNIQUE ("outbox_id", "attempt_number")
);

CREATE INDEX IF NOT EXISTS "email_delivery_attempts_outbox_idx"
    ON "public"."email_delivery_attempts" ("outbox_id", "attempt_number" DESC);

ALTER TABLE "public"."email_outbox" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."email_delivery_attempts" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "public"."email_outbox"
    FROM PUBLIC, "anon", "authenticated";
REVOKE ALL ON TABLE "public"."email_delivery_attempts"
    FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT, UPDATE ON TABLE "public"."email_outbox" TO "service_role";
GRANT SELECT, INSERT, UPDATE ON TABLE "public"."email_delivery_attempts" TO "service_role";

-- The roster keeps a deliberately smaller projection than the operational
-- outbox. Webhook-ready delivery is additive; terminal failures still project
-- as `failed` and never alter invitation authorization state.
ALTER TABLE "public"."platform_admin_invitations"
    DROP CONSTRAINT IF EXISTS "platform_admin_invitations_email_delivery_status_check";
ALTER TABLE "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_email_delivery_status_check"
    CHECK ("email_delivery_status" = ANY (ARRAY[
        'pending'::text, 'sent'::text, 'delivered'::text, 'failed'::text
    ]));

CREATE OR REPLACE FUNCTION "public"."phase717_cancel_terminal_invitation_email"()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF NEW."status" <> 'invited'::text AND OLD."status" = 'invited'::text THEN
        UPDATE "public"."email_outbox"
        SET "status" = 'cancelled'::text, "locked_at" = NULL,
            "protected_token" = NULL, "updated_at" = now(),
            "last_error_category" = 'INVITATION_TERMINAL'::text
        WHERE "aggregate_id" = NEW."invitation_id"
          AND "status" = 'pending'::text;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER "trg_phase717_cancel_terminal_invitation_email"
    AFTER UPDATE OF "status" ON "public"."platform_admin_invitations"
    FOR EACH ROW EXECUTE FUNCTION "public"."phase717_cancel_terminal_invitation_email"();
REVOKE ALL ON FUNCTION "public"."phase717_cancel_terminal_invitation_email"() FROM PUBLIC;

UPDATE "public"."platform_admin_invitations"
SET "status" = 'expired'::text, "updated_at" = now()
WHERE "status" = 'invited'::text AND "expires_at" <= now();

CREATE UNIQUE INDEX IF NOT EXISTS "platform_admin_invitations_one_pending_email_idx"
    ON "public"."platform_admin_invitations" ("institution_id", lower("email"))
    WHERE "status" = 'invited'::text;

CREATE OR REPLACE FUNCTION "public"."phase717_create_invitation_with_outbox"(
    "p_institution_id" uuid,
    "p_email" text,
    "p_token_hash" text,
    "p_expires_at" timestamp with time zone,
    "p_created_by" uuid,
    "p_protected_token" text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    -- Preserve the prior service behaviour: an elapsed row is terminalized
    -- before issuing a replacement, while a still-live duplicate is rejected
    -- by the partial unique index even under concurrent requests.
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
        p_institution_id, lower(btrim(p_email)), p_token_hash, 'admin'::text,
        'invited'::text, p_expires_at, p_created_by, 'pending'::text
    ) RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (v_invitation."invitation_id", p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase717_rotate_invitation_with_outbox"(
    "p_invitation_id" uuid,
    "p_token_hash" text,
    "p_expires_at" timestamp with time zone,
    "p_expected_updated_at" timestamp with time zone,
    "p_protected_token" text,
    "p_lock_seconds" integer
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    SELECT * INTO v_invitation
    FROM "public"."platform_admin_invitations"
    WHERE "invitation_id" = p_invitation_id
    FOR UPDATE;

    IF NOT FOUND OR v_invitation."status" <> 'invited'::text
       OR v_invitation."expires_at" <= now()
       OR (p_expected_updated_at IS NOT NULL
           AND v_invitation."updated_at" IS DISTINCT FROM p_expected_updated_at) THEN
        RETURN NULL;
    END IF;

    -- Recover an abandoned lease before deciding whether resend can proceed.
    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = 'retry'::text, "completed_at" = now(),
        "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id"
      AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."aggregate_id" = p_invitation_id
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds);

    -- A non-stale worker may already be inside provider I/O. Refuse the resend
    -- rather than rotate the token underneath that delivery.
    IF EXISTS (
        SELECT 1 FROM "public"."email_outbox"
        WHERE "aggregate_id" = p_invitation_id
          AND "status" = 'processing'::text
    ) THEN
        RETURN NULL;
    END IF;

    UPDATE "public"."email_outbox"
    SET "status" = 'cancelled'::text, "locked_at" = NULL,
        "protected_token" = NULL, "updated_at" = now(),
        "last_error_category" = 'INVITATION_SUPERSEDED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'pending'::text;

    UPDATE "public"."platform_admin_invitations"
    SET "token_hash" = p_token_hash, "expires_at" = p_expires_at,
        "resend_count" = "resend_count" + 1,
        "email_delivery_status" = 'pending'::text,
        "email_delivery_at" = NULL, "updated_at" = now()
    WHERE "invitation_id" = p_invitation_id
    RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (p_invitation_id, p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase717_claim_email_outbox"(
    "p_batch_size" integer,
    "p_lock_seconds" integer,
    "p_retry_limit" integer
) RETURNS SETOF "public"."email_outbox"
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    -- Jobs whose invitation is terminal or elapsed cannot produce a usable
    -- URL and must not remain pending forever.
    UPDATE "public"."email_outbox" AS o
    SET "status" = 'cancelled'::text, "protected_token" = NULL,
        "updated_at" = now(),
        "last_error_category" = 'INVITATION_NOT_DELIVERABLE'::text
    FROM "public"."platform_admin_invitations" AS i
    WHERE i."invitation_id" = o."aggregate_id"
      AND o."status" = 'pending'::text
      AND (i."status" <> 'invited'::text OR i."expires_at" <= now());

    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = CASE WHEN o."attempt_count" >= p_retry_limit
                        THEN 'dead_letter'::text ELSE 'retry'::text END,
        "completed_at" = now(), "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id" AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'dead_letter'::text, "locked_at" = NULL,
        "protected_token" = NULL,
        "failed_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds)
      AND "attempt_count" >= p_retry_limit;

    UPDATE "public"."platform_admin_invitations" AS i
    SET "email_delivery_status" = 'failed'::text,
        "email_delivery_at" = now(), "updated_at" = now()
    FROM "public"."email_outbox" AS o
    WHERE o."aggregate_id" = i."invitation_id"
      AND o."status" = 'dead_letter'::text
      AND o."last_error_category" = 'WORKER_LEASE_EXPIRED'::text;

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds)
      AND "attempt_count" < p_retry_limit;

    RETURN QUERY
    WITH eligible AS (
        SELECT o."id"
        FROM "public"."email_outbox" AS o
        JOIN "public"."platform_admin_invitations" AS i
          ON i."invitation_id" = o."aggregate_id"
        WHERE o."status" = 'pending'::text
          AND o."available_at" <= now()
          AND o."attempt_count" < p_retry_limit
          AND i."status" = 'invited'::text
          AND i."expires_at" > now()
        ORDER BY o."available_at", o."created_at"
        FOR UPDATE OF o SKIP LOCKED
        LIMIT LEAST(GREATEST(p_batch_size, 1), 200)
    ), claimed AS (
        UPDATE "public"."email_outbox" AS o
        SET "status" = 'processing'::text, "locked_at" = now(),
            "attempt_count" = o."attempt_count" + 1, "updated_at" = now()
        FROM eligible AS e WHERE o."id" = e."id"
        RETURNING o.*
    ), attempts AS (
        INSERT INTO "public"."email_delivery_attempts"
            ("outbox_id", "attempt_number", "started_at", "result")
        SELECT c."id", c."attempt_count", now(), 'processing'::text FROM claimed AS c
        RETURNING "outbox_id"
    )
    SELECT c.* FROM claimed AS c JOIN attempts AS a ON a."outbox_id" = c."id";
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase717_complete_email_outbox"(
    "p_outbox_id" uuid,
    "p_attempt_number" integer,
    "p_outcome" text,
    "p_provider_name" text,
    "p_provider_message_id" text DEFAULT NULL,
    "p_failure_category" text DEFAULT NULL,
    "p_available_at" timestamp with time zone DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_outbox "public"."email_outbox"%ROWTYPE;
    v_invitation_status text;
BEGIN
    IF p_outcome NOT IN ('sent'::text, 'retry'::text, 'dead_letter'::text, 'cancelled'::text) THEN
        RAISE EXCEPTION 'invalid email outbox outcome' USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO v_outbox FROM "public"."email_outbox"
    WHERE "id" = p_outbox_id FOR UPDATE;
    IF NOT FOUND OR v_outbox."status" <> 'processing'::text
       OR v_outbox."attempt_count" <> p_attempt_number THEN
        RETURN false;
    END IF;

    UPDATE "public"."email_delivery_attempts"
    SET "completed_at" = now(), "result" = p_outcome,
        "failure_category" = p_failure_category,
        "provider_message_id" = p_provider_message_id
    WHERE "outbox_id" = p_outbox_id AND "attempt_number" = p_attempt_number
      AND "result" = 'processing'::text;

    UPDATE "public"."email_outbox"
    SET "status" = CASE WHEN p_outcome = 'retry'::text THEN 'pending'::text
                        ELSE p_outcome END,
        "locked_at" = NULL,
        "available_at" = CASE WHEN p_outcome = 'retry'::text
                              THEN COALESCE(p_available_at, now())
                              ELSE "available_at" END,
        "sent_at" = CASE WHEN p_outcome = 'sent'::text THEN now() ELSE "sent_at" END,
        "failed_at" = CASE WHEN p_outcome = 'dead_letter'::text THEN now() ELSE "failed_at" END,
        "provider_name" = NULLIF(btrim(p_provider_name), ''),
        "provider_message_id" = p_provider_message_id,
        "last_error_category" = p_failure_category,
        "protected_token" = CASE WHEN p_outcome = 'retry'::text
                                 THEN "protected_token" ELSE NULL END,
        "delivery_updated_at" = now(), "updated_at" = now()
    WHERE "id" = p_outbox_id;

    v_invitation_status := CASE
        WHEN p_outcome = 'sent'::text THEN 'sent'::text
        WHEN p_outcome IN ('dead_letter'::text, 'cancelled'::text) THEN 'failed'::text
        ELSE 'pending'::text END;
    UPDATE "public"."platform_admin_invitations"
    SET "email_delivery_status" = v_invitation_status,
        "email_delivery_at" = now(),
        "email_delivery_attempts" = "email_delivery_attempts" + 1,
        "last_sent_at" = CASE WHEN p_outcome = 'sent'::text THEN now()
                              ELSE "last_sent_at" END,
        "updated_at" = now()
    WHERE "invitation_id" = v_outbox."aggregate_id";
    RETURN true;
END;
$$;

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
            'expires_at', i."expires_at"
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

REVOKE ALL ON FUNCTION "public"."phase717_create_invitation_with_outbox"(
    uuid, text, text, timestamp with time zone, uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION "public"."phase717_rotate_invitation_with_outbox"(
    uuid, text, timestamp with time zone, timestamp with time zone, text, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION "public"."phase717_claim_email_outbox"(
    integer, integer, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION "public"."phase717_complete_email_outbox"(
    uuid, integer, text, text, text, text, timestamp with time zone) FROM PUBLIC;
REVOKE ALL ON FUNCTION "public"."phase717_resolve_email_outbox_context"(
    uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION "public"."phase717_create_invitation_with_outbox"(
    uuid, text, text, timestamp with time zone, uuid, text) TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase717_rotate_invitation_with_outbox"(
    uuid, text, timestamp with time zone, timestamp with time zone, text, integer) TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase717_claim_email_outbox"(
    integer, integer, integer) TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase717_complete_email_outbox"(
    uuid, integer, text, text, text, text, timestamp with time zone) TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase717_resolve_email_outbox_context"(
    uuid, text) TO "service_role";

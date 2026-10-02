-- Phase 7.18 -- durable, idempotent Mailgun delivery-event reconciliation.
-- Rollback plan: drop phase718_reconcile_mailgun_event, then drop
-- email_delivery_events and the delivery_sequence column/index. Existing
-- Phase 7.17 provider-correlation and state columns are reused.

ALTER TABLE "public"."email_outbox"
    ADD COLUMN IF NOT EXISTS "delivery_sequence" bigint
    GENERATED ALWAYS AS IDENTITY;
CREATE UNIQUE INDEX IF NOT EXISTS "email_outbox_delivery_sequence_idx"
    ON "public"."email_outbox" ("delivery_sequence");

CREATE TABLE IF NOT EXISTS "public"."email_delivery_events" (
    "id" uuid DEFAULT gen_random_uuid() NOT NULL,
    "provider_name" text NOT NULL,
    "event_key" text NOT NULL,
    "replay_token_digest" text NOT NULL,
    "provider_event_id" text NOT NULL,
    "provider_message_id" text,
    "event_type" text NOT NULL,
    "event_timestamp" timestamp with time zone NOT NULL,
    "outbox_id" uuid,
    "processing_result" text DEFAULT 'received'::text NOT NULL,
    "state_changed" boolean DEFAULT false NOT NULL,
    "received_at" timestamp with time zone DEFAULT now() NOT NULL,
    "processed_at" timestamp with time zone,
    CONSTRAINT "email_delivery_events_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "email_delivery_events_outbox_fkey" FOREIGN KEY ("outbox_id")
        REFERENCES "public"."email_outbox" ("id") ON DELETE SET NULL,
    CONSTRAINT "email_delivery_events_provider_key_key"
        UNIQUE ("provider_name", "event_key"),
    CONSTRAINT "email_delivery_events_replay_token_key"
        UNIQUE ("provider_name", "replay_token_digest"),
    CONSTRAINT "email_delivery_events_digest_check"
        CHECK (length("event_key") = 64 AND length("replay_token_digest") = 64),
    CONSTRAINT "email_delivery_events_result_check" CHECK (
        "processing_result" = ANY (ARRAY[
            'received'::text, 'applied'::text, 'no_state_change'::text,
            'stale_generation'::text, 'unknown_message'::text,
            'unsupported'::text
        ])
    )
);

CREATE INDEX IF NOT EXISTS "email_delivery_events_message_idx"
    ON "public"."email_delivery_events" ("provider_name", "provider_message_id");
CREATE INDEX IF NOT EXISTS "email_delivery_events_outbox_idx"
    ON "public"."email_delivery_events" ("outbox_id", "event_timestamp" DESC);

ALTER TABLE "public"."email_delivery_events" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "public"."email_delivery_events"
    FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT, UPDATE ON TABLE "public"."email_delivery_events"
    TO "service_role";

CREATE OR REPLACE FUNCTION "public"."phase718_reconcile_mailgun_event"(
    "p_event_key" text,
    "p_replay_token_digest" text,
    "p_provider_event_id" text,
    "p_provider_message_id" text,
    "p_event_type" text,
    "p_event_timestamp" timestamp with time zone
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_event_id uuid;
    v_outbox "public"."email_outbox"%ROWTYPE;
    v_new_status text;
    v_result text;
    v_changed boolean := false;
    v_is_latest boolean := false;
BEGIN
    IF length(p_event_key) <> 64 OR length(p_replay_token_digest) <> 64
       OR NULLIF(btrim(p_provider_event_id), '') IS NULL
       OR p_event_timestamp IS NULL THEN
        RAISE EXCEPTION 'invalid verified email event' USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO "public"."email_delivery_events" (
        "provider_name", "event_key", "replay_token_digest",
        "provider_event_id", "provider_message_id", "event_type",
        "event_timestamp"
    ) VALUES (
        'mailgun'::text, p_event_key, p_replay_token_digest,
        p_provider_event_id, NULLIF(btrim(p_provider_message_id), ''),
        p_event_type, p_event_timestamp
    ) ON CONFLICT DO NOTHING
    RETURNING "id" INTO v_event_id;

    IF v_event_id IS NULL THEN
        RETURN jsonb_build_object(
            'result', 'duplicate', 'state_changed', false
        );
    END IF;

    IF p_event_type = 'unsupported'::text THEN
        UPDATE "public"."email_delivery_events"
        SET "processing_result" = 'unsupported'::text, "processed_at" = now()
        WHERE "id" = v_event_id;
        RETURN jsonb_build_object(
            'result', 'unsupported', 'state_changed', false
        );
    END IF;

    SELECT * INTO v_outbox
    FROM "public"."email_outbox"
    WHERE "provider_name" = 'mailgun'::text
      AND "provider_message_id" = NULLIF(btrim(p_provider_message_id), '')
    FOR UPDATE;

    IF NOT FOUND THEN
        UPDATE "public"."email_delivery_events"
        SET "processing_result" = 'unknown_message'::text, "processed_at" = now()
        WHERE "id" = v_event_id;
        RETURN jsonb_build_object(
            'result', 'unknown_message', 'state_changed', false
        );
    END IF;

    UPDATE "public"."email_delivery_events"
    SET "outbox_id" = v_outbox."id"
    WHERE "id" = v_event_id;

    SELECT NOT EXISTS (
        SELECT 1 FROM "public"."email_outbox" AS newer
        WHERE newer."aggregate_id" = v_outbox."aggregate_id"
          AND newer."delivery_sequence" > v_outbox."delivery_sequence"
    ) INTO v_is_latest;

    v_new_status := v_outbox."status";
    IF p_event_type = 'delivered'::text AND v_outbox."status" = 'sent'::text THEN
        v_new_status := 'delivered'::text;
    ELSIF p_event_type IN ('permanent_failure'::text, 'rejected'::text)
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        v_new_status := 'bounced'::text;
    ELSIF p_event_type = 'complained'::text
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        v_new_status := 'complained'::text;
    END IF;

    v_changed := v_new_status IS DISTINCT FROM v_outbox."status";
    IF v_changed THEN
        UPDATE "public"."email_outbox"
        SET "status" = v_new_status,
            "last_error_category" = CASE
                WHEN p_event_type = 'temporary_failure'::text
                    THEN 'MAILGUN_TEMPORARY_FAILURE'::text
                WHEN p_event_type IN ('permanent_failure'::text, 'rejected'::text)
                    THEN 'MAILGUN_PERMANENT_FAILURE'::text
                WHEN p_event_type = 'complained'::text
                    THEN 'MAILGUN_COMPLAINT'::text
                ELSE "last_error_category" END,
            "delivery_updated_at" = p_event_timestamp,
            "updated_at" = now()
        WHERE "id" = v_outbox."id";
    ELSIF p_event_type = 'temporary_failure'::text
          AND v_outbox."status" IN ('sent'::text, 'delivered'::text) THEN
        UPDATE "public"."email_outbox"
        SET "last_error_category" = 'MAILGUN_TEMPORARY_FAILURE'::text,
            "delivery_updated_at" = p_event_timestamp, "updated_at" = now()
        WHERE "id" = v_outbox."id";
    END IF;

    -- An event for an older send is retained on that outbox row but cannot
    -- overwrite the invitation projection for a newer resend generation.
    IF v_is_latest AND v_changed THEN
        UPDATE "public"."platform_admin_invitations"
        SET "email_delivery_status" = CASE
                WHEN v_new_status = 'delivered'::text THEN 'delivered'::text
                ELSE 'failed'::text END,
            "email_delivery_at" = p_event_timestamp,
            "updated_at" = now()
        WHERE "invitation_id" = v_outbox."aggregate_id";
    END IF;

    v_result := CASE
        WHEN NOT v_is_latest THEN 'stale_generation'::text
        WHEN v_changed THEN 'applied'::text
        ELSE 'no_state_change'::text END;
    UPDATE "public"."email_delivery_events"
    SET "processing_result" = v_result, "state_changed" = v_changed,
        "processed_at" = now()
    WHERE "id" = v_event_id;

    RETURN jsonb_build_object(
        'result', v_result,
        'state_changed', v_changed,
        'outbox_id', v_outbox."id"
    );
END;
$$;

REVOKE ALL ON FUNCTION "public"."phase718_reconcile_mailgun_event"(
    text, text, text, text, text, timestamp with time zone) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION "public"."phase718_reconcile_mailgun_event"(
    text, text, text, text, text, timestamp with time zone) TO "service_role";


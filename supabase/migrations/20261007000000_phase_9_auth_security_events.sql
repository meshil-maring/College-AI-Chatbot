-- Append-only security events for authentication and password lifecycle actions.
-- Credentials, access/refresh tokens, reset tokens, and email addresses are
-- deliberately excluded from the event payload.

CREATE TABLE IF NOT EXISTS "public"."auth_security_events" (
    "event_id" uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" uuid,
    "auth_user_id" uuid,
    "event" text NOT NULL,
    "status" text NOT NULL,
    "ip_address" inet,
    "user_agent" text,
    "occurred_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "auth_security_events_pkey" PRIMARY KEY ("event_id"),
    CONSTRAINT "auth_security_events_user_id_fkey"
        FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL,
    CONSTRAINT "auth_security_events_event_not_blank_check"
        CHECK ("btrim"("event") <> ''),
    CONSTRAINT "auth_security_events_status_check"
        CHECK ("status" = ANY (ARRAY['success'::text, 'failure'::text, 'info'::text]))
);

CREATE INDEX IF NOT EXISTS "idx_auth_security_events_user_time"
    ON "public"."auth_security_events" ("user_id", "occurred_at" DESC);
CREATE INDEX IF NOT EXISTS "idx_auth_security_events_auth_user_time"
    ON "public"."auth_security_events" ("auth_user_id", "occurred_at" DESC);

ALTER TABLE "public"."auth_security_events" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "public"."auth_security_events" FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT ON TABLE "public"."auth_security_events" TO "service_role";

COMMENT ON TABLE "public"."auth_security_events" IS
    'Append-only authentication security event trail; contains no credentials or bearer tokens.';

-- The provider remains responsible for issuing and validating recovery
-- sessions. This table stores only a one-way fingerprint to make a verified
-- recovery session single-use at the application boundary.
CREATE TABLE IF NOT EXISTS "public"."auth_consumed_password_recovery_sessions" (
    "session_fingerprint" text NOT NULL,
    "auth_user_id" uuid NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "consumed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "auth_consumed_password_recovery_sessions_pkey"
        PRIMARY KEY ("session_fingerprint"),
    CONSTRAINT "auth_consumed_password_recovery_sessions_fingerprint_check"
        CHECK ("session_fingerprint" ~ '^[0-9a-f]{64}$')
);

ALTER TABLE "public"."auth_consumed_password_recovery_sessions"
    ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "public"."auth_consumed_password_recovery_sessions"
    FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT, DELETE ON TABLE "public"."auth_consumed_password_recovery_sessions"
    TO "service_role";

CREATE OR REPLACE FUNCTION "public"."consume_auth_password_recovery_session"(
    "p_session_fingerprint" text,
    "p_auth_user_id" uuid,
    "p_expires_at" timestamp with time zone
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    inserted_rows integer;
BEGIN
    DELETE FROM "public"."auth_consumed_password_recovery_sessions"
    WHERE "expires_at" <= pg_catalog.now();

    INSERT INTO "public"."auth_consumed_password_recovery_sessions" (
        "session_fingerprint",
        "auth_user_id",
        "expires_at"
    )
    VALUES (
        "p_session_fingerprint",
        "p_auth_user_id",
        "p_expires_at"
    )
    ON CONFLICT ("session_fingerprint") DO NOTHING;

    GET DIAGNOSTICS inserted_rows = ROW_COUNT;
    RETURN inserted_rows = 1;
END;
$function$;

REVOKE ALL ON FUNCTION "public"."consume_auth_password_recovery_session"(
    text, uuid, timestamp with time zone
) FROM PUBLIC, "anon", "authenticated";
GRANT EXECUTE ON FUNCTION "public"."consume_auth_password_recovery_session"(
    text, uuid, timestamp with time zone
) TO "service_role";

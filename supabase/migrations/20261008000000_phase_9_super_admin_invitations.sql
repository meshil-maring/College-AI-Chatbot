-- Phase 9: invitation-only Super Admin registration.
--
-- A Super Admin invites a person by email. The invitee follows a single-use,
-- expiring link and sets their own password; the platform-scoped super_admin
-- grant is then assigned server-side through phase712_assign_super_admin.
-- Only the SHA-256 digest of the token is stored.

CREATE TABLE IF NOT EXISTS "public"."platform_super_admin_invitations" (
    "invitation_id" uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "email" text NOT NULL,
    "token_hash" text NOT NULL,
    "status" text DEFAULT 'invited'::text NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "created_by" uuid NOT NULL,
    "accepted_user_id" uuid,
    "accepted_at" timestamp with time zone,
    "cancelled_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "platform_super_admin_invitations_pkey" PRIMARY KEY ("invitation_id"),
    CONSTRAINT "platform_super_admin_invitations_token_hash_key" UNIQUE ("token_hash"),
    CONSTRAINT "platform_super_admin_invitations_status_check"
        CHECK ("status" = ANY (ARRAY['invited'::text, 'accepted'::text, 'cancelled'::text, 'expired'::text])),
    CONSTRAINT "platform_super_admin_invitations_email_check"
        CHECK ("email" = "lower"("btrim"("email")) AND "length"("email") <= 320),
    CONSTRAINT "platform_super_admin_invitations_created_by_fkey"
        FOREIGN KEY ("created_by") REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    CONSTRAINT "platform_super_admin_invitations_accepted_user_fkey"
        FOREIGN KEY ("accepted_user_id") REFERENCES "public"."users" ("id") ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS "uq_platform_super_admin_invitations_pending_email"
    ON "public"."platform_super_admin_invitations" ("email")
    WHERE "status" = 'invited';

ALTER TABLE "public"."platform_super_admin_invitations" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "public"."platform_super_admin_invitations" FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT, UPDATE ON TABLE "public"."platform_super_admin_invitations" TO "service_role";

COMMENT ON TABLE "public"."platform_super_admin_invitations" IS
    'Phase 9 single-use invitations for creating additional Super Admin accounts.';

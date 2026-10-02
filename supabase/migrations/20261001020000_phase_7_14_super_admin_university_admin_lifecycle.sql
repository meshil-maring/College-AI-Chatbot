-- ===========================================================================
-- Phase 7.14 — Super Admin University Admin lifecycle
--
-- REUSED ENTITY (no duplicate model)
--   public.institutions           (EXISTING, canonical tenant)
--   public.users                  (EXISTING application identity)
--   public.user_roles / roles     (EXISTING RBAC; Phase 7.12 super_admin,
--                                   Phase 6.13 institution-scoped admin)
--   public.platform_institution_audit_log  (EXISTING, Phase 7.13; extended)
--
-- DELIBERATE NON-CHANGES
--   * No new user/role/institution/tenant/auth table. An invitation is a
--     credential for the EXISTING registration + RBAC primitives.
--   * No password column, no password hash, no plaintext token column. The
--     raw invitation token exists only in the one HTTP response that created
--     it; the database stores only its SHA-256 digest.
--   * This migration creates NO Auth identity and assigns NO role to a person.
-- ===========================================================================

-- ===========================================================================
-- A. platform_admin_invitations — one-time, expiring University Admin invitations
--
-- An invitation binds EXACTLY ONE institution and EXACTLY ONE role name
-- (CHECK below is hard-coded to 'admin'), so it can never be used to obtain
-- access to another institution and can never mint a platform role.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS "public"."platform_admin_invitations" (
    "invitation_id" uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id" uuid NOT NULL
        REFERENCES "public"."institutions" ("institution_id") ON DELETE RESTRICT,
    "email" text NOT NULL,
    -- SHA-256 hex digest of the one-time raw token. The raw token is NEVER
    -- persisted, so a database read cannot reconstruct a usable credential.
    "token_hash" text NOT NULL,
    "role_name" text DEFAULT 'admin'::text NOT NULL,
    "status" text DEFAULT 'invited'::text NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "accepted_at" timestamp with time zone,
    "cancelled_at" timestamp with time zone,
    "accepted_user_id" uuid
        REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "created_by" uuid NOT NULL
        REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "platform_admin_invitations_pkey" PRIMARY KEY ("invitation_id"),
    CONSTRAINT "platform_admin_invitations_token_hash_key" UNIQUE ("token_hash"),
    CONSTRAINT "platform_admin_invitations_role_name_check"
        CHECK ("role_name" = 'admin'::text),
    CONSTRAINT "platform_admin_invitations_status_check"
        CHECK ("status" = ANY (ARRAY[
            'invited'::text, 'accepted'::text, 'cancelled'::text, 'expired'::text
        ])),
    CONSTRAINT "platform_admin_invitations_email_check"
        CHECK ("btrim"("email") <> '' AND "email" = "lower"("btrim"("email"))
               AND "length"("email") <= 320),
    CONSTRAINT "platform_admin_invitations_token_hash_check"
        CHECK ("token_hash" ~ '^[0-9a-f]{64}$'),
    -- An invitation must be usable for a strictly positive window.
    CONSTRAINT "platform_admin_invitations_expiry_check"
        CHECK ("expires_at" > "created_at"),
    -- Terminal states carry their transition timestamp; the two terminal
    -- timestamps are mutually exclusive so a row can never claim to have been
    -- both accepted and cancelled.
    CONSTRAINT "platform_admin_invitations_terminal_state_check"
        CHECK (
            (
                "status" = 'invited'::text
                AND "accepted_at" IS NULL
                AND "cancelled_at" IS NULL
                AND "accepted_user_id" IS NULL
            )
            OR (
                "status" = 'accepted'::text
                AND "accepted_at" IS NOT NULL
                AND "cancelled_at" IS NULL
            )
            OR (
                "status" = 'cancelled'::text
                AND "cancelled_at" IS NOT NULL
                AND "accepted_at" IS NULL
            )
            OR (
                "status" = 'expired'::text
                AND "accepted_at" IS NULL
                AND "cancelled_at" IS NULL
            )
        )
);

COMMENT ON TABLE "public"."platform_admin_invitations" IS
    'Phase 7.14 one-time, expiring University Admin invitations. Stores only a SHA-256 token digest; never a raw token or password.';

-- Roster: pending/terminal invitations for one institution.
CREATE INDEX IF NOT EXISTS "platform_admin_invitations_institution_status_idx"
    ON "public"."platform_admin_invitations" ("institution_id", "status");

-- Expiry sweep: only outstanding invitations can ever expire.
CREATE INDEX IF NOT EXISTS "platform_admin_invitations_status_expiry_idx"
    ON "public"."platform_admin_invitations" ("status", "expires_at");

-- Duplicate-pending-invitation check for one invitee.
CREATE INDEX IF NOT EXISTS "platform_admin_invitations_email_idx"
    ON "public"."platform_admin_invitations" ("email");
-- ===========================================================================
-- B. Lifecycle transition guard
--
-- invited -> accepted | cancelled | expired
-- accepted | cancelled | expired are TERMINAL: a consumed, cancelled or expired
-- invitation can never be revived, so an accepted token cannot be replayed and
-- a cancelled token can never be used. This is enforced in the database, not
-- only in application code.
-- ===========================================================================

CREATE OR REPLACE FUNCTION "public"."phase714_assert_invitation_transition"()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF NEW."status" IS DISTINCT FROM OLD."status" THEN
        IF OLD."status" <> 'invited'::text THEN
            RAISE EXCEPTION 'Phase 7.14: invitation % is already terminal', OLD."status"
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW."status" NOT IN ('accepted'::text, 'cancelled'::text, 'expired'::text) THEN
            RAISE EXCEPTION 'Phase 7.14: invalid invitation transition'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- The binding of an invitation is immutable: an invitation can never be
    -- re-pointed at another institution, another email, or another role.
    IF NEW."institution_id" IS DISTINCT FROM OLD."institution_id"
       OR NEW."role_name" IS DISTINCT FROM OLD."role_name"
       OR NEW."token_hash" IS DISTINCT FROM OLD."token_hash"
       OR NEW."email" IS DISTINCT FROM OLD."email"
       OR NEW."created_by" IS DISTINCT FROM OLD."created_by"
       OR NEW."expires_at" IS DISTINCT FROM OLD."expires_at"
       OR NEW."created_at" IS DISTINCT FROM OLD."created_at" THEN
        RAISE EXCEPTION 'Phase 7.14: invitation identity is immutable'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS "trg_phase714_invitation_transition"
    ON "public"."platform_admin_invitations";

CREATE TRIGGER "trg_phase714_invitation_transition"
    BEFORE UPDATE ON "public"."platform_admin_invitations"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase714_assert_invitation_transition"();

-- The invitation table holds credential-adjacent material (a token digest).
-- It is reachable ONLY through the backend service-role client, exactly like
-- the Phase 7.12 / Phase 7.13 ledgers. No anon/authenticated/RLS path exists.
REVOKE ALL ON TABLE "public"."platform_admin_invitations"
    FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT, UPDATE ON TABLE "public"."platform_admin_invitations" TO "service_role";

REVOKE ALL ON FUNCTION "public"."phase714_assert_invitation_transition"() FROM PUBLIC;
-- ===========================================================================
-- C. Extend the Phase 7.13 audit ledger with the University Admin lifecycle
--
-- The Phase 7.13 CHECK constrained `action` to the institution CRUD vocabulary.
-- The constraint is dropped and recreated with the additive Phase 7.14
-- vocabulary; every existing row keeps its value and its audit_id, so no
-- historical entry is rewritten or deleted.
--
-- `details` stays a bounded, non-sensitive jsonb summary. It NEVER contains a
-- raw invitation token, a token hash, a password, or a service-role key.
-- ===========================================================================

ALTER TABLE "public"."platform_institution_audit_log"
    DROP CONSTRAINT IF EXISTS "platform_institution_audit_action_check";

ALTER TABLE "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_action_check" CHECK (
        "action" = ANY (ARRAY[
            'institution_created'::text,
            'institution_updated'::text,
            'institution_suspended'::text,
            'institution_activated'::text,
            'admin_assigned'::text,
            -- Phase 7.14 University Admin lifecycle
            'institution_admin_invited'::text,
            'institution_admin_invitation_accepted'::text,
            'institution_admin_invitation_expired'::text,
            'institution_admin_invitation_cancelled'::text,
            'institution_admin_revoked'::text
        ])
    );

ALTER TABLE "public"."platform_institution_audit_log"
    DROP CONSTRAINT IF EXISTS "platform_institution_audit_result_check";

ALTER TABLE "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_result_check" CHECK (
        "result" = ANY (ARRAY[
            'success'::text, 'already_applied'::text, 'denied'::text
        ])
    );

-- Read-only audit listing (Super Admin, newest first) with the optional
-- institution/time filters exposed by GET /api/v1/platform/audit.
CREATE INDEX IF NOT EXISTS "idx_platform_institution_audit_time"
    ON "public"."platform_institution_audit_log" ("performed_at" DESC);

CREATE INDEX IF NOT EXISTS "idx_platform_institution_audit_action_time"
    ON "public"."platform_institution_audit_log" ("action", "performed_at" DESC);

COMMENT ON CONSTRAINT "platform_institution_audit_action_check"
    ON "public"."platform_institution_audit_log" IS
    'Phase 7.14: institution CRUD + University Admin invitation/revocation vocabulary. No credential material is representable.';

-- Read-only visibility for the platform audit API. INSERT remains available to
-- the service role (audit writes happen server-side); no UPDATE/DELETE grant
-- exists, so the ledger is append-only for every client.
GRANT SELECT ON TABLE "public"."platform_institution_audit_log" TO "service_role";
REVOKE UPDATE, DELETE ON TABLE "public"."platform_institution_audit_log"
    FROM PUBLIC, "anon", "authenticated", "service_role";

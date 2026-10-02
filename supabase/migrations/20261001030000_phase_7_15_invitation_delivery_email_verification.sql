-- ===========================================================================
-- Phase 7.15 — Invitation delivery, email verification & abuse controls
--
-- REUSED ENTITY (no duplicate model)
--   public.platform_admin_invitations       (EXISTING, Phase 7.14; extended)
--   public.platform_institution_audit_log   (EXISTING, Phase 7.13/7.14; extended)
--   public.institutions / users / user_roles  (UNCHANGED)
--
-- DELIBERATE NON-CHANGES
--   * No new table. An invitation is still ONE row; delivery is bookkeeping on
--     that row, not a messaging platform and not an outbox table.
--   * No new lifecycle state. `status` keeps exactly the Phase 7.14 vocabulary
--     (invited / accepted / cancelled / expired) and its terminal-state
--     semantics, so no redundant lifecycle field is introduced.
--   * No password column, no token column. The raw token still exists only in
--     the one HTTP response that minted it; only its SHA-256 digest is stored.
--   * No email-provider credential column. Credentials live in server-side
--     environment configuration only and never reach the database.
-- ===========================================================================

-- ===========================================================================
-- A. Delivery + verification bookkeeping (additive columns only)
--
-- Every column has a demonstrated requirement:
--   email_verified_at       the server-authoritative email-ownership fact,
--                           surfaced to the acceptance page and the roster.
--                           Set ONLY by acceptance, never client-asserted.
--   email_delivery_status   lets a Super Admin tell "the link exists" apart
--                           from "the email actually went out".
--   email_delivery_at       when the last attempt happened (triage + retry).
--   email_delivery_attempts how many attempts were made (abuse observability).
--   last_sent_at            when a send last SUCCEEDED.
--   resend_count            how often the link was reissued (roster signal).
--
-- There is deliberately no column for a message body, subject, recipient list
-- or provider response: none is needed after delivery, and storing them would
-- widen the credential-adjacent surface for no benefit.
-- ===========================================================================

ALTER TABLE "public"."platform_admin_invitations"
    ADD COLUMN IF NOT EXISTS "email_verified_at" timestamp with time zone;

ALTER TABLE "public"."platform_admin_invitations"
    ADD COLUMN IF NOT EXISTS "email_delivery_status" text
        DEFAULT 'pending'::text NOT NULL;

ALTER TABLE "public"."platform_admin_invitations"
    ADD COLUMN IF NOT EXISTS "email_delivery_at" timestamp with time zone;

ALTER TABLE "public"."platform_admin_invitations"
    ADD COLUMN IF NOT EXISTS "email_delivery_attempts" integer
        DEFAULT 0 NOT NULL;

ALTER TABLE "public"."platform_admin_invitations"
    ADD COLUMN IF NOT EXISTS "last_sent_at" timestamp with time zone;

ALTER TABLE "public"."platform_admin_invitations"
    ADD COLUMN IF NOT EXISTS "resend_count" integer DEFAULT 0 NOT NULL;

ALTER TABLE "public"."platform_admin_invitations"
    DROP CONSTRAINT IF EXISTS "platform_admin_invitations_email_delivery_status_check";

ALTER TABLE "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_email_delivery_status_check"
    CHECK ("email_delivery_status" = ANY (ARRAY[
        'pending'::text, 'sent'::text, 'failed'::text
    ]));

ALTER TABLE "public"."platform_admin_invitations"
    DROP CONSTRAINT IF EXISTS "platform_admin_invitations_delivery_attempts_check";

ALTER TABLE "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_delivery_attempts_check"
    CHECK ("email_delivery_attempts" >= 0);

ALTER TABLE "public"."platform_admin_invitations"
    DROP CONSTRAINT IF EXISTS "platform_admin_invitations_resend_count_check";

ALTER TABLE "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_resend_count_check"
    CHECK ("resend_count" >= 0);

-- An invitation can only be VERIFIED once it has been accepted: verification is
-- a consequence of a successful, server-authoritative acceptance, so it is
-- structurally impossible for a still-pending invitation to look verified.
ALTER TABLE "public"."platform_admin_invitations"
    DROP CONSTRAINT IF EXISTS "platform_admin_invitations_verified_requires_accepted_check";

ALTER TABLE "public"."platform_admin_invitations"
    ADD CONSTRAINT "platform_admin_invitations_verified_requires_accepted_check"
    CHECK (
        "email_verified_at" IS NULL
        OR ("status" = 'accepted'::text AND "accepted_at" IS NOT NULL)
    );

COMMENT ON COLUMN "public"."platform_admin_invitations"."email_verified_at" IS
    'Phase 7.15: set by the server only, after acceptance proved the Auth account carries exactly this invitation''s email. Never client-asserted.';

COMMENT ON COLUMN "public"."platform_admin_invitations"."email_delivery_status" IS
    'Phase 7.15: pending | sent | failed. Bookkeeping about delivery attempts only - never a lifecycle state.';

-- Roster view: which pending invitations were actually mailed.
CREATE INDEX IF NOT EXISTS "platform_admin_invitations_delivery_status_idx"
    ON "public"."platform_admin_invitations" ("email_delivery_status")
    WHERE "status" = 'invited'::text;

-- ===========================================================================
-- B. Lifecycle trigger: permit token rotation for a PENDING invitation only
--
-- The Phase 7.14 trigger made `token_hash` and `expires_at` immutable so an
-- invitation's binding could never be rewritten. Resend needs exactly one
-- narrow exception: while the row is still `invited`, its token digest and
-- expiry MAY be replaced, because that is how a superseded link is closed and
-- a new one issued in the same row (one live URL per invitation, always).
--
-- Everything else stays exactly as strict as Phase 7.14:
--   * institution_id, role_name, email, created_by and created_at remain
--     IMMUTABLE for the life of the row, so an invitation can never be
--     re-pointed at another tenant, another role or another person;
--   * terminal states remain terminal: an accepted, cancelled or expired
--     invitation can never return to `invited` or have its token rotated;
--   * the allowed transition set is unchanged.
-- ===========================================================================

CREATE OR REPLACE FUNCTION "public"."phase715_assert_invitation_transition"()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF NEW."status" IS DISTINCT FROM OLD."status" THEN
        IF OLD."status" <> 'invited'::text THEN
            RAISE EXCEPTION 'Phase 7.15: invitation % is already terminal', OLD."status"
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW."status" NOT IN ('accepted'::text, 'cancelled'::text, 'expired'::text) THEN
            RAISE EXCEPTION 'Phase 7.15: invalid invitation transition'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- The invitation's BINDING is immutable for its whole life: the tenant, the
    -- role, the invited person and the issuing Super Admin never change, and
    -- neither does the creation timestamp.
    IF NEW."institution_id" IS DISTINCT FROM OLD."institution_id"
       OR NEW."role_name" IS DISTINCT FROM OLD."role_name"
       OR NEW."email" IS DISTINCT FROM OLD."email"
       OR NEW."created_by" IS DISTINCT FROM OLD."created_by"
       OR NEW."created_at" IS DISTINCT FROM OLD."created_at" THEN
        RAISE EXCEPTION 'Phase 7.15: invitation identity is immutable'
            USING ERRCODE = 'check_violation';
    END IF;

    -- Token rotation is permitted ONLY while the invitation is still pending
    -- AND the row is not transitioning to a terminal state in the same
    -- statement. A terminal invitation keeps its digest forever, so a
    -- superseded, consumed, cancelled or expired token can never be revived.
    IF (NEW."token_hash" IS DISTINCT FROM OLD."token_hash"
        OR NEW."expires_at" IS DISTINCT FROM OLD."expires_at") THEN
        IF OLD."status" <> 'invited'::text
           OR NEW."status" IS DISTINCT FROM OLD."status" THEN
            RAISE EXCEPTION 'Phase 7.15: only a pending invitation token may be rotated'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Verification may only be recorded on an already-accepted row (enforced
    -- again here so the invariant holds even if the CHECK is ever dropped),
    -- and it may never be un-recorded.
    IF OLD."email_verified_at" IS NOT NULL
       AND NEW."email_verified_at" IS DISTINCT FROM OLD."email_verified_at" THEN
        RAISE EXCEPTION 'Phase 7.15: email verification is irreversible'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS "trg_phase714_invitation_transition"
    ON "public"."platform_admin_invitations";

DROP TRIGGER IF EXISTS "trg_phase715_invitation_transition"
    ON "public"."platform_admin_invitations";

CREATE TRIGGER "trg_phase715_invitation_transition"
    BEFORE UPDATE ON "public"."platform_admin_invitations"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase715_assert_invitation_transition"();

REVOKE ALL ON FUNCTION "public"."phase715_assert_invitation_transition"() FROM PUBLIC;

-- ===========================================================================
-- C. Extend the audit ledger with the delivery / resend / verification events
--
-- Purely ADDITIVE: the Phase 7.14 vocabulary is preserved verbatim, so every
-- existing row keeps its value and its audit_id. No historical entry is
-- rewritten or deleted, and no existing event is renamed or duplicated.
--
--   institution_admin_invitation_email_sent    delivery succeeded
--   institution_admin_invitation_email_failed  delivery failed; the invitation
--                                               stays live and resendable
--   institution_admin_invitation_resent        a token was superseded + re-sent
--   institution_admin_invitation_verified      the server established email
--                                               ownership during acceptance
--
-- `result` gains 'failed' so a delivery failure is representable without
-- overloading 'denied' (which means an authorization refusal).
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
            -- Phase 7.14 University Admin lifecycle (unchanged)
            'institution_admin_invited'::text,
            'institution_admin_invitation_accepted'::text,
            'institution_admin_invitation_expired'::text,
            'institution_admin_invitation_cancelled'::text,
            'institution_admin_revoked'::text,
            -- Phase 7.15 invitation delivery / email verification (additive)
            'institution_admin_invitation_email_sent'::text,
            'institution_admin_invitation_email_failed'::text,
            'institution_admin_invitation_resent'::text,
            'institution_admin_invitation_verified'::text
        ])
    );

ALTER TABLE "public"."platform_institution_audit_log"
    DROP CONSTRAINT IF EXISTS "platform_institution_audit_result_check";

ALTER TABLE "public"."platform_institution_audit_log"
    ADD CONSTRAINT "platform_institution_audit_result_check" CHECK (
        "result" = ANY (ARRAY[
            'success'::text, 'already_applied'::text, 'denied'::text,
            'failed'::text
        ])
    );

COMMENT ON CONSTRAINT "platform_institution_audit_action_check"
    ON "public"."platform_institution_audit_log" IS
    'Phase 7.15: institution CRUD + University Admin invitation lifecycle + invitation delivery/verification vocabulary. No credential material is representable.';

COMMENT ON TABLE "public"."platform_admin_invitations" IS
    'Phase 7.14 one-time, expiring University Admin invitations, extended in Phase 7.15 with delivery and email-verification bookkeeping. Stores only a SHA-256 token digest; never a raw token, password or provider credential.';

-- Grants are unchanged: the table is still service-role only. No anon or
-- authenticated path exists, and Phase 7.15 adds no new read surface.
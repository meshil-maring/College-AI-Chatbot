-- ============================================================================
-- Phase 7.13 — Super Admin Institution Management
-- ============================================================================
-- REUSED ENTITY (no duplicate tenant model)
--   public.institutions  (EXISTING, canonical tenant boundary)
--       |  institution_id  -- unchanged primary key; students, knowledge,
--       |                     documents, campuses and departments all already
--       |                     reference THIS column
--       |  code             -- EXISTING globally UNIQUE public routing
--       |                     identifier; already consumed by
--       |                     /public-chat/{institution_code} and /u/{code}
--       |  name             -- EXISTING
--       |  status           -- EXISTING Phase 6.13 CHECK
--       |                     ('pending'|'active'|'suspended'|'rejected')
--
-- This migration therefore does NOT create a university / college /
-- institution / tenant / organization table. Phase 7.13 extends the canonical
-- row and reuses the Phase 6.13 lifecycle vocabulary verbatim: the platform
-- lifecycle is expressed with the SAME 'active' <-> 'suspended' status values
-- the existing database already enforces, so no overlapping status system is
-- introduced and every existing guard keeps working unchanged.
--
-- DELIBERATE NON-CHANGES
--   * No `slug` column. The existing `code` already fulfils the user-facing
--     URL identifier requirement for BOTH /public-chat/{institution_code}
--     and the Phase 7.11 /u/{institution-code} route. Adding a slug would be a
--     second source of truth for the same public identifier, so Phase 7.13
--     keeps the smallest possible schema change.
--   * No rewrite of any existing institution code. institutions_code_key
--     (UNIQUE on code) already exists from the baseline; Phase 7.13 only adds
--     a case-insensitive uniqueness INDEX as defence in depth so a future
--     lowercase insert cannot silently create a second routing identity.
--   * No data deletion, no student/document/knowledge reassignment.
-- ============================================================================

-- ============================================================================
-- A. Branding foundation (additive, all nullable)
-- ============================================================================
-- Branding is OPTIONAL. Institution creation requires only name + code; every
-- column below defaults to NULL and the public gateway falls back to the
-- existing neutral local defaults when a value is absent. No existing row is
-- modified and no backfill is performed.

ALTER TABLE "public"."institutions"
    ADD COLUMN IF NOT EXISTS "display_name" text,
    ADD COLUMN IF NOT EXISTS "logo_url" text,
    ADD COLUMN IF NOT EXISTS "primary_color" text,
    ADD COLUMN IF NOT EXISTS "secondary_color" text,
    ADD COLUMN IF NOT EXISTS "welcome_message" text;

COMMENT ON COLUMN "public"."institutions"."display_name" IS
    'Phase 7.13 optional branding: public display name (falls back to name).';
COMMENT ON COLUMN "public"."institutions"."logo_url" IS
    'Phase 7.13 optional branding: public logo image URL.';
COMMENT ON COLUMN "public"."institutions"."primary_color" IS
    'Phase 7.13 optional branding: primary accent colour (CSS hex).';
COMMENT ON COLUMN "public"."institutions"."secondary_color" IS
    'Phase 7.13 optional branding: secondary accent colour (CSS hex).';
COMMENT ON COLUMN "public"."institutions"."welcome_message" IS
    'Phase 7.13 optional branding: public gateway welcome message.';

-- Deterministic case handling for the public routing identifier. Codes are
-- normalized to UPPER by the service layer; this index makes a case-variant
-- duplicate structurally impossible rather than merely discouraged.
CREATE UNIQUE INDEX IF NOT EXISTS "institutions_code_upper_key"
    ON "public"."institutions" (upper("code"));

-- ============================================================================
-- B. Reserved platform parent organization
-- ============================================================================
-- Phase 6.13 made institutions.organization_id NOT NULL with an FK, so an
-- institution cannot exist without an owning organization. Super Admin
-- institution creation must require ONLY name + code, so this migration creates
-- one reserved, platform-owned parent group that the narrow create flow uses.
--
-- It is deliberately a single reserved row keyed by a fixed code, NOT a second
-- tenant hierarchy: the organization -> institution relationship stays exactly
-- as Phase 6.13 defined it, and no existing organization or institution is
-- modified.

INSERT INTO "public"."organizations" (
    "name", "organization_code", "official_email", "contact_information", "status"
) VALUES (
    'College AI Platform Institutions',
    'COLLEGE-AI-PLATFORM',
    'platform-institutions@local.invalid',
    'Reserved parent organization for institutions created through the Super Admin platform API.',
    'active'
)
ON CONFLICT ("organization_code") DO NOTHING;

-- ============================================================================
-- C. platform_institution_audit_log — auditable institution management
-- ============================================================================
-- Reuses the Phase 7.12 service-role-only audit pattern (the same REVOKE/GRANT
-- shape as platform_role_audit_log) with an institution-shaped target. A
-- dedicated table is used because Phase 7.12's ledger is constrained to the
-- super_admin role lifecycle (role_name CHECK + assign/revoke action CHECK),
-- which cannot represent institution create/update/suspend/activate.
--
-- Recorded per the Phase 7.13 audit requirements:
--   actor_user_id  — acting super_admin's public.users row (server-resolved)
--   action         — institution_created | institution_updated |
--                    institution_suspended | institution_activated |
--                    admin_assigned
--   institution_id — target institution (a resource id, never authorization)
--   target_user_id — only for admin_assigned (the assigned account)
--   performed_at   — timestamp
--   result         — success | already_applied
--
-- `details` is a bounded, non-sensitive jsonb summary (changed field names and
-- codes only). It NEVER stores passwords, access tokens, service-role keys, or
-- any other credential.

CREATE TABLE IF NOT EXISTS "public"."platform_institution_audit_log" (
    "audit_id" uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    "actor_user_id" uuid NOT NULL
        REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "action" text NOT NULL,
    "institution_id" uuid NOT NULL
        REFERENCES "public"."institutions" ("institution_id") ON DELETE RESTRICT,
    "target_user_id" uuid
        REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "result" text DEFAULT 'success'::text NOT NULL,
    "details" jsonb DEFAULT '{}'::jsonb NOT NULL,
    "performed_at" timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT "platform_institution_audit_action_check" CHECK (
        "action" = ANY (ARRAY[
            'institution_created'::text,
            'institution_updated'::text,
            'institution_suspended'::text,
            'institution_activated'::text,
            'admin_assigned'::text
        ])
    ),
    CONSTRAINT "platform_institution_audit_result_check" CHECK (
        "result" = ANY (ARRAY['success'::text, 'already_applied'::text])
    )
);

CREATE INDEX IF NOT EXISTS "idx_platform_institution_audit_target_time"
    ON "public"."platform_institution_audit_log" ("institution_id", "performed_at" DESC);

REVOKE ALL ON TABLE "public"."platform_institution_audit_log"
    FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT ON TABLE "public"."platform_institution_audit_log" TO "service_role";

COMMENT ON TABLE "public"."platform_institution_audit_log" IS
    'Phase 7.13 service-role-only audit ledger for Super Admin institution management.';

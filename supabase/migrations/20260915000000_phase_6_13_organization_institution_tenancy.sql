-- ============================================================================
-- Phase 6.13 - Organization, Institution & Authentication (tenancy foundation)
-- ============================================================================
-- Introduces the Organization -> Institution hierarchy on top of the EXISTING
-- tenant model and extends RBAC with an explicit SCOPE.
--
-- ARCHITECTURE (extends Phase 6.1/6.2 - no model is replaced)
--
--     organizations                (NEW)
--          |  organization_id
--     institutions                 (EXISTING table, +organization_id, +status)
--          |  institution_id  <-- STILL the one and only tenant key
--     users                        (EXISTING)
--          |  user_id
--     user_roles                   (EXISTING, +scope_type/+scope_id)
--     students                     (EXISTING, untouched)
--
-- NON-DUPLICATION DECISIONS (field names are conceptual, existing columns win)
--
--   * institution_code   -> EXISTING institutions.code          (global UNIQUE)
--   * official_email     -> EXISTING institutions.email
--   * location           -> EXISTING institutions.address
--   * institutions.is_active remains the compatibility flag read by the locked
--     Phase 6.2/6.5/6.3 code paths (student registration + student login). The
--     new authoritative `status` column drives it through a trigger, so there
--     is exactly ONE source of truth and no code path can observe an
--     inconsistent pair.
--   * students.approval_status is NOT extended: 'pending' already IS the
--     "registered / pending approval" state and 'approved' + is_active=true IS
--     "active". Adding a parallel vocabulary would break the locked Phase 6.4
--     state machine (pending -> approved | rejected, strict).
--   * user_roles keeps its existing (user_id, role_id) primary key. Scope is
--     ADDITIVE columns, so every existing ON CONFLICT (user_id, role_id) and
--     every existing RBAC read keeps working unchanged.
--
-- BACKFILL (documented, safe, idempotent)
--
--   1. A single legacy organization is created for institutions that predate
--      this phase, and every existing institution is linked to it. Status is
--      derived from the existing is_active flag so no institution changes
--      availability as a result of this migration.
--   2. Every existing user_roles row is backfilled to the EXACT scope it
--      already had implicitly:
--          user has a students profile  -> scope_type='institution',
--                                          scope_id=students.institution_id
--          user has no students profile -> scope_type='platform', scope_id=NULL
--      This reproduces get_user_by_auth_id()'s current tenant resolution, so
--      Phase 6.6 tenant-isolation behaviour is unchanged.
--   3. No existing row is deleted, no institution_id is rewritten, no user is
--      recreated, and no document/embedding is touched.
--
-- Future institutions (Delhi, Kolkata, Head Office) are added purely as new
-- institutions rows under the same organization - no data migration, no id
-- change, no re-embedding of existing knowledge.
-- ============================================================================


-- ============================================================================
-- A. organizations
-- ============================================================================

CREATE TABLE IF NOT EXISTS "public"."organizations" (
    "organization_id"    uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "name"               text NOT NULL,
    -- Public, human-usable organization handle (e.g. NIELIT). NEVER the
    -- internal uuid: this is what registration/login flows accept.
    "organization_code"  text NOT NULL,
    "official_email"     text NOT NULL,
    "contact_information" text NOT NULL,
    "status"             text DEFAULT 'pending'::text NOT NULL,
    -- Optional organization-issued join code. When set, an institution join
    -- request must present it (verified server-side, constant time) in addition
    -- to the organization_code, so "typing an organization name" is never
    -- sufficient. Approval by an organization admin remains the authoritative
    -- gate.
    "join_code"          text,
    "created_at"         timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"         timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "organizations_name_check" CHECK (("btrim"("name") <> ''::text)),
    CONSTRAINT "organizations_code_check" CHECK ((
        "organization_code" = "upper"("btrim"("organization_code"))
        AND "btrim"("organization_code") <> ''
    )),
    CONSTRAINT "organizations_email_check" CHECK ((
        "official_email" = "btrim"("lower"("official_email"))
    )),
    CONSTRAINT "organizations_contact_check" CHECK ((
        "btrim"("contact_information") <> ''
    )),
    CONSTRAINT "organizations_status_check" CHECK (("status" = ANY (ARRAY[
        'pending'::text,
        'active'::text,
        'suspended'::text,
        'rejected'::text
    ]))),
    CONSTRAINT "organizations_join_code_check" CHECK ((
        "join_code" IS NULL OR "btrim"("join_code") <> ''
    ))
);

ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_pkey" PRIMARY KEY ("organization_id");

ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_organization_code_key" UNIQUE ("organization_code");

ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_join_code_key" UNIQUE ("join_code");

CREATE INDEX IF NOT EXISTS "idx_organizations_status"
    ON "public"."organizations" ("status");

CREATE INDEX IF NOT EXISTS "idx_organizations_name"
    ON "public"."organizations" ("name");

COMMENT ON TABLE "public"."organizations" IS
    'Top-level tenant group (Phase 6.13). An organization owns 1..n institutions.';
CREATE UNIQUE INDEX IF NOT EXISTS "uq_organizations_code_lower"
    ON "public"."organizations" ("lower"("organization_code"));


-- ============================================================================
-- B. institutions - organization link + authoritative status
-- ============================================================================
-- ADDITIVE ONLY. institutions.institution_id stays the single tenant key used by
-- every locked Phase 6.1-6.11 code path. No institution id, code, document,
-- embedding, student, or user is rewritten by this migration.
--
-- Non-duplication: the conceptual fields from the Phase 6.13 specification map
-- onto columns that already exist, so no duplicate column is created.
--
--     institution_code -> institutions.code     (already globally UNIQUE)
--     official_email   -> institutions.email
--     location         -> institutions.address / city / state / country

ALTER TABLE "public"."institutions"
    ADD COLUMN IF NOT EXISTS "organization_id" uuid;

ALTER TABLE "public"."institutions"
    ADD COLUMN IF NOT EXISTS "status" text;


-- ----------------------------------------------------------------------------
-- B-1. Backfill the legacy organization for institutions that predate this phase
-- ----------------------------------------------------------------------------
-- Exactly one organization row is created, and ONLY when at least one
-- institution lacks an organization. Re-running the migration is idempotent:
-- the existing 'LEGACY-INSTITUTIONS' organization is reused instead of
-- duplicated. Existing institutions keep their institution_id and code, so all
-- previously attached documents, chunks, embeddings, students, and users remain
-- associated with their original institution.

DO $$
DECLARE
    legacy_organization_id uuid;
    legacy_email           text;
    orphan_count           integer;
BEGIN
    SELECT count(*)
        INTO orphan_count
        FROM "public"."institutions"
        WHERE "organization_id" IS NULL;

    IF orphan_count = 0 THEN
        RETURN;
    END IF;

    SELECT "organization_id"
        INTO legacy_organization_id
        FROM "public"."organizations"
        WHERE "organization_code" = 'LEGACY-INSTITUTIONS'
        LIMIT 1;

    IF legacy_organization_id IS NULL THEN
        -- Contact data is derived from the existing institution rows rather than
        -- invented, so the placeholder organization stays truthful.
        SELECT "lower"("btrim"(COALESCE("ci"."email", "ci"."code" || '@legacy.invalid')))
            INTO legacy_email
            FROM "public"."institutions" AS "ci"
            WHERE "ci"."organization_id" IS NULL
            ORDER BY "ci"."created_at"
            LIMIT 1;

        INSERT INTO "public"."organizations" (
            "name",
            "organization_code",
            "official_email",
            "contact_information",
            "status"
        ) VALUES (
            'Legacy Institution Group',
            'LEGACY-INSTITUTIONS',
            COALESCE(legacy_email, 'legacy@legacy.invalid'),
            'Placeholder organization created by the Phase 6.13 tenancy migration '
            'to group institutions that existed before the organization model. '
            'Replace by registering a real organization and re-assigning '
            'institutions through the institution join/approval flow.',
            'active'
        )
        RETURNING "organization_id" INTO legacy_organization_id;
    END IF;

    UPDATE "public"."institutions"
        SET "organization_id" = legacy_organization_id
        WHERE "organization_id" IS NULL;
END;
$$;


-- ----------------------------------------------------------------------------
-- B-2. Status <-> is_active single source of truth
-- ----------------------------------------------------------------------------
-- `status` is the new AUTHORITATIVE lifecycle column (pending / active /
-- suspended / rejected). `is_active` stays exactly as it is, because locked
-- Phase 6.2/6.3/6.5 code (student registration + student sign-in) reads it.
-- A BEFORE trigger derives is_active from status on every write, so the pair
-- can never disagree and no existing read path changes meaning.
--
-- Backfill maps the current availability onto the new vocabulary:
--     is_active = true  -> status = 'active'
--     is_active = false -> status = 'suspended'
-- No institution therefore changes availability as a result of this migration.

UPDATE "public"."institutions"
    SET "status" = CASE
        WHEN "is_active" IS TRUE THEN 'active'
        ELSE 'suspended'
    END
    WHERE "status" IS NULL;

ALTER TABLE "public"."institutions"
    ALTER COLUMN "status" SET DEFAULT 'pending'::text;

ALTER TABLE "public"."institutions"
    ALTER COLUMN "status" SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM "pg_constraint"
        WHERE "conname" = 'institutions_status_check'
          AND "conrelid" = '"public"."institutions"'::"regclass"
    ) THEN
        ALTER TABLE "public"."institutions"
            ADD CONSTRAINT "institutions_status_check" CHECK (("status" = ANY (ARRAY[
                'pending'::text,
                'active'::text,
                'suspended'::text,
                'rejected'::text
            ])));
    END IF;
END;
$$;

-- Every institution must belong to a valid organization. The FK makes an
-- orphan institution structurally impossible (not merely a validation rule).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM "pg_constraint"
        WHERE "conname" = 'institutions_organization_id_fkey'
          AND "conrelid" = '"public"."institutions"'::"regclass"
    ) THEN
        ALTER TABLE "public"."institutions"
            ADD CONSTRAINT "institutions_organization_id_fkey"
            FOREIGN KEY ("organization_id")
            REFERENCES "public"."organizations" ("organization_id");
    END IF;
END;
$$;

ALTER TABLE "public"."institutions"
    ALTER COLUMN "organization_id" SET NOT NULL;

CREATE OR REPLACE FUNCTION "public"."phase613_sync_institution_status"()
RETURNS "trigger"
LANGUAGE "plpgsql"
AS $$
BEGIN
    IF "NEW"."status" IS NULL THEN
        "NEW"."status" := CASE WHEN "NEW"."is_active" IS TRUE THEN 'active' ELSE 'suspended' END;
    END IF;

    -- status is authoritative: only 'active' means the institution is usable.
    IF "NEW"."status" = 'active' THEN
        "NEW"."is_active" := true;
    ELSE
        "NEW"."is_active" := false;
    END IF;

    RETURN "NEW";
END;
$$;

DROP TRIGGER IF EXISTS "trg_phase613_institutions_status" ON "public"."institutions";

CREATE TRIGGER "trg_phase613_institutions_status"
    BEFORE INSERT OR UPDATE ON "public"."institutions"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase613_sync_institution_status"();

CREATE INDEX IF NOT EXISTS "idx_institutions_organization_id"
    ON "public"."institutions" ("organization_id");

CREATE INDEX IF NOT EXISTS "idx_institutions_organization_status"
    ON "public"."institutions" ("organization_id", "status");

CREATE INDEX IF NOT EXISTS "idx_institutions_status"
    ON "public"."institutions" ("status");

COMMENT ON COLUMN "public"."institutions"."organization_id" IS
    'Owning organization (Phase 6.13). NOT NULL: every institution belongs to exactly one organization.';
COMMENT ON COLUMN "public"."institutions"."status" IS
    'Authoritative lifecycle status (Phase 6.13). Derived flag is_active is kept in sync by trigger trg_phase613_institutions_status.';


-- ============================================================================
-- C. institution_join_requests — secure institution -> organization joining
-- ============================================================================
-- An institution never joins an organization by "typing its name". It registers
-- with the organization's PUBLIC code (organizations.organization_code) plus the
-- organization-issued join_code when one exists, and the request stays PENDING
-- until an organization-scoped admin approves it. The organization admin is the
-- only authority that can move the request to approved/rejected.
--
-- The institution row is created immediately in status 'pending' (=> is_active
-- false via the B-2 trigger) so it holds no resources and cannot be used for
-- registration/login until approval. Nothing is deleted on rejection: the
-- request and the institution row are retained as history.

CREATE TABLE IF NOT EXISTS "public"."institution_join_requests" (
    "join_request_id"        uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "organization_id"        uuid NOT NULL,
    "institution_id"         uuid NOT NULL,
    -- Public institution code typed at request time, kept for the audit trail.
    "requested_institution_code" text NOT NULL,
    "requested_by_user_id"   uuid NOT NULL,
    "status"                 text DEFAULT 'pending'::text NOT NULL,
    "decision_reason"        text,
    "decided_by_user_id"     uuid,
    "decided_at"             timestamp with time zone,
    "created_at"             timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"             timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "institution_join_requests_status_check" CHECK (("status" = ANY (ARRAY[
        'pending'::text,
        'approved'::text,
        'rejected'::text
    ]))),
    CONSTRAINT "institution_join_requests_code_check" CHECK ((
        "requested_institution_code" = "upper"("btrim"("requested_institution_code"))
        AND "btrim"("requested_institution_code") <> ''::text
    )),
    -- A decided request must record who decided it and when; a pending request
    -- must not carry a decision. This makes an unattributed approval impossible.
    CONSTRAINT "institution_join_requests_decision_check" CHECK ((
        ("status" = 'pending'::text AND "decided_by_user_id" IS NULL AND "decided_at" IS NULL)
        OR ("status" <> 'pending'::text AND "decided_by_user_id" IS NOT NULL AND "decided_at" IS NOT NULL)
    ))
);

ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_pkey" PRIMARY KEY ("join_request_id");

ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_organization_id_fkey"
    FOREIGN KEY ("organization_id") REFERENCES "public"."organizations" ("organization_id");

ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_institution_id_fkey"
    FOREIGN KEY ("institution_id") REFERENCES "public"."institutions" ("institution_id");

ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_requested_by_fkey"
    FOREIGN KEY ("requested_by_user_id") REFERENCES "public"."users" ("user_id");

ALTER TABLE ONLY "public"."institution_join_requests"
    ADD CONSTRAINT "institution_join_requests_decided_by_fkey"
    FOREIGN KEY ("decided_by_user_id") REFERENCES "public"."users" ("user_id");

-- At most ONE open request per institution: re-requesting after a rejection is
-- allowed, a second concurrent pending request is not.
CREATE UNIQUE INDEX IF NOT EXISTS "uq_institution_join_request_open"
    ON "public"."institution_join_requests" ("institution_id")
    WHERE "status" = 'pending'::text;

CREATE INDEX IF NOT EXISTS "idx_institution_join_requests_organization_status"
    ON "public"."institution_join_requests" ("organization_id", "status");

CREATE INDEX IF NOT EXISTS "idx_institution_join_requests_status"
    ON "public"."institution_join_requests" ("status");

CREATE INDEX IF NOT EXISTS "idx_institution_join_requests_requested_by"
    ON "public"."institution_join_requests" ("requested_by_user_id");

COMMENT ON TABLE "public"."institution_join_requests" IS
    'Phase 6.13 institution-to-organization join requests. Approval by an organization-scoped admin is the only way an institution becomes active.';


-- ============================================================================
-- D. user_roles — explicit ROLE + SCOPE (no new roles are introduced)
-- ============================================================================
-- The Phase 6.13 requirement "role + scope" is implemented as ADDITIVE columns
-- on the EXISTING user_roles table. The primary key stays (user_id, role_id), so
-- every existing read (app/db/supabase.py user_roles join) and every existing
-- ON CONFLICT (user_id, role_id) keeps working unchanged.
--
--   scope_type = 'platform'     -> platform-level account (no tenant)
--   scope_type = 'organization' -> organization admin (scope_id = organization)
--   scope_type = 'institution'  -> institution-scoped user (scope_id = institution)
--
-- scope_organization_id is the denormalized parent organization, so
-- organization-scoped authorization is a single indexed comparison instead of a
-- join. Backfill reproduces the CURRENT implicit semantics exactly:
--   * user with a students profile -> institution scope of that institution
--   * user without one            -> platform scope (previous behaviour)

ALTER TABLE "public"."user_roles"
    ADD COLUMN IF NOT EXISTS "scope_type" text;

ALTER TABLE "public"."user_roles"
    ADD COLUMN IF NOT EXISTS "scope_id" uuid;

ALTER TABLE "public"."user_roles"
    ADD COLUMN IF NOT EXISTS "scope_organization_id" uuid;

UPDATE "public"."user_roles" AS "ur"
    SET "scope_type" = 'institution',
        "scope_id" = "s"."institution_id",
        "scope_organization_id" = "i"."organization_id"
    FROM "public"."students" AS "s"
    JOIN "public"."institutions" AS "i"
      ON "i"."institution_id" = "s"."institution_id"
    WHERE "ur"."user_id" = "s"."user_id"
      AND "ur"."scope_type" IS NULL;

UPDATE "public"."user_roles"
    SET "scope_type" = 'platform',
        "scope_id" = NULL,
        "scope_organization_id" = NULL
    WHERE "scope_type" IS NULL;

ALTER TABLE "public"."user_roles"
    ALTER COLUMN "scope_type" SET DEFAULT 'platform'::text;

ALTER TABLE "public"."user_roles"
    ALTER COLUMN "scope_type" SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM "pg_constraint"
        WHERE "conname" = 'user_roles_scope_check'
          AND "conrelid" = '"public"."user_roles"'::"regclass"
    ) THEN
        ALTER TABLE "public"."user_roles"
            ADD CONSTRAINT "user_roles_scope_check" CHECK ((
                ("scope_type" = 'platform'::text AND "scope_id" IS NULL
                    AND "scope_organization_id" IS NULL)
                OR ("scope_type" = 'organization'::text AND "scope_id" IS NOT NULL
                    AND "scope_organization_id" = "scope_id")
                OR ("scope_type" = 'institution'::text AND "scope_id" IS NOT NULL
                    AND "scope_organization_id" IS NOT NULL)
            ));
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS "idx_user_roles_scope_type_scope_id"
    ON "public"."user_roles" ("scope_type", "scope_id");

CREATE INDEX IF NOT EXISTS "idx_user_roles_scope_organization"
    ON "public"."user_roles" ("scope_organization_id");

CREATE INDEX IF NOT EXISTS "idx_user_roles_user_scope"
    ON "public"."user_roles" ("user_id", "scope_type");

COMMENT ON COLUMN "public"."user_roles"."scope_type" IS
    'Phase 6.13 authorization scope: platform | organization | institution.';
COMMENT ON COLUMN "public"."user_roles"."scope_id" IS
    'Phase 6.13 scope target id: organization_id for organization scope, institution_id for institution scope.';
COMMENT ON COLUMN "public"."user_roles"."scope_organization_id" IS
    'Phase 6.13 denormalized parent organization used for organization-bound authorization.';


-- ============================================================================
-- E. institution_membership_requests — staff / faculty onboarding
-- ============================================================================
-- Faculty and staff NEVER receive a role by registering. Registration only
-- creates a PENDING request that an institution-scoped admin (or an
-- organization-scoped admin for an institution inside their organization)
-- must approve. The role is written to user_roles by the server during
-- approval - never by the client, and never by this table.
--
-- Defense in depth: requested_role has a CHECK constraint restricted to the
-- two non-privileged academic roles. 'admin' is not representable at the
-- database level, so a bug or compromise in the API layer still cannot
-- persist a privilege-escalation request.
--
-- The table is a REQUEST LEDGER, not a second RBAC source of truth: the only
-- authoritative grant remains user_roles (Phase 6.13 scope columns above).

CREATE TABLE IF NOT EXISTS "public"."institution_membership_requests" (
    "request_id"            uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "institution_id"        uuid NOT NULL,
    -- Denormalized parent organization so organization-scoped admins can list
    -- their approvals without a join.
    "organization_id"       uuid NOT NULL,
    "user_id"               uuid NOT NULL,
    -- Only staff | faculty. 'admin' / 'student' are structurally impossible.
    "requested_role"        text NOT NULL,
    "official_email"        text NOT NULL,
    "full_name"             text,
    "designation"           text,
    "department"            text,
    "status"                text DEFAULT 'pending'::text NOT NULL,
    "decision_reason"       text,
    "decided_by_user_id"    uuid,
    "decided_at"            timestamp with time zone,
    "created_at"            timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at"            timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "institution_membership_requests_role_check" CHECK ((
        "requested_role" = ANY (ARRAY['staff'::text, 'faculty'::text])
    )),
    CONSTRAINT "institution_membership_requests_status_check" CHECK (("status" = ANY (ARRAY[
        'pending'::text,
        'approved'::text,
        'rejected'::text
    ]))),
    CONSTRAINT "institution_membership_requests_email_check" CHECK ((
        "official_email" = "btrim"("lower"("official_email"))
    )),
    -- A decided request must record who decided it and when; a pending request
    -- must not carry a decision (mirrors institution_join_requests).
    CONSTRAINT "institution_membership_requests_decision_check" CHECK ((
        ("status" = 'pending'::text AND "decided_by_user_id" IS NULL AND "decided_at" IS NULL)
        OR ("status" <> 'pending'::text AND "decided_by_user_id" IS NOT NULL AND "decided_at" IS NOT NULL)
    ))
);

ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_pkey" PRIMARY KEY ("request_id");

ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_institution_id_fkey"
    FOREIGN KEY ("institution_id") REFERENCES "public"."institutions" ("institution_id");

ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_organization_id_fkey"
    FOREIGN KEY ("organization_id") REFERENCES "public"."organizations" ("organization_id");

ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."users" ("user_id");

ALTER TABLE ONLY "public"."institution_membership_requests"
    ADD CONSTRAINT "institution_membership_requests_decided_by_fkey"
    FOREIGN KEY ("decided_by_user_id") REFERENCES "public"."users" ("user_id");

-- At most ONE open request per (user, requested role). Re-requesting after a
-- rejection is allowed; a second concurrent pending request is not.
CREATE UNIQUE INDEX IF NOT EXISTS "uq_institution_membership_request_open"
    ON "public"."institution_membership_requests" ("user_id", "requested_role")
    WHERE "status" = 'pending'::text;

CREATE INDEX IF NOT EXISTS "idx_institution_membership_requests_inst_status"
    ON "public"."institution_membership_requests" ("institution_id", "status");

CREATE INDEX IF NOT EXISTS "idx_institution_membership_requests_org_status"
    ON "public"."institution_membership_requests" ("organization_id", "status");

CREATE INDEX IF NOT EXISTS "idx_institution_membership_requests_user_id"
    ON "public"."institution_membership_requests" ("user_id");

COMMENT ON TABLE "public"."institution_membership_requests" IS
    'Phase 6.13 staff/faculty onboarding requests. Approval by an authorized admin is the ONLY path that grants the role; the request row never grants access by itself.';


-- ============================================================================
-- F. Integrity guards
-- ============================================================================
-- Invariants that must hold even if a future code path (or a direct SQL write)
-- tries to violate them:
--
--   1. A child row's denormalized organization_id must equal the owning
--      institution's organization_id. Cross-organization attachment is
--      therefore structurally impossible, not merely validated in Python.
--   2. A user_roles row with institution scope must reference an institution
--      whose organization matches scope_organization_id.

CREATE OR REPLACE FUNCTION "public"."phase613_assert_child_organization"()
RETURNS "trigger"
LANGUAGE "plpgsql"
AS $$
DECLARE
    institution_organization_id uuid;
BEGIN
    SELECT "i"."organization_id"
        INTO institution_organization_id
        FROM "public"."institutions" AS "i"
        WHERE "i"."institution_id" = "NEW"."institution_id";

    IF institution_organization_id IS NULL THEN
        RAISE EXCEPTION 'Phase 6.13: institution % does not exist', "NEW"."institution_id"
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF "NEW"."organization_id" IS DISTINCT FROM institution_organization_id THEN
        RAISE EXCEPTION
            'Phase 6.13: organization % does not own institution % (expected %)',
            "NEW"."organization_id", "NEW"."institution_id", institution_organization_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN "NEW";
END;
$$;

DROP TRIGGER IF EXISTS "trg_phase613_membership_request_organization"
    ON "public"."institution_membership_requests";

CREATE TRIGGER "trg_phase613_membership_request_organization"
    BEFORE INSERT OR UPDATE ON "public"."institution_membership_requests"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase613_assert_child_organization"();

DROP TRIGGER IF EXISTS "trg_phase613_join_request_organization"
    ON "public"."institution_join_requests";

CREATE TRIGGER "trg_phase613_join_request_organization"
    BEFORE INSERT OR UPDATE ON "public"."institution_join_requests"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase613_assert_child_organization"();

CREATE OR REPLACE FUNCTION "public"."phase613_assert_role_scope"()
RETURNS "trigger"
LANGUAGE "plpgsql"
AS $$
DECLARE
    institution_organization_id uuid;
BEGIN
    IF "NEW"."scope_type" <> 'institution'::text THEN
        RETURN "NEW";
    END IF;

    SELECT "i"."organization_id"
        INTO institution_organization_id
        FROM "public"."institutions" AS "i"
        WHERE "i"."institution_id" = "NEW"."scope_id";

    IF institution_organization_id IS NULL
       OR institution_organization_id IS DISTINCT FROM "NEW"."scope_organization_id" THEN
        RAISE EXCEPTION
            'Phase 6.13: institution scope % is not inside organization scope %',
            "NEW"."scope_id", "NEW"."scope_organization_id"
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN "NEW";
END;
$$;

DROP TRIGGER IF EXISTS "trg_phase613_user_roles_scope" ON "public"."user_roles";

CREATE TRIGGER "trg_phase613_user_roles_scope"
    BEFORE INSERT OR UPDATE OF "scope_type", "scope_id", "scope_organization_id"
    ON "public"."user_roles"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase613_assert_role_scope"();


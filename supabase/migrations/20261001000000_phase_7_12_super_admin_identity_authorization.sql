-- Phase 7.12 — Super Admin identity and authorization foundation
--
-- This migration defines the platform-scoped role and controlled service-role
-- provisioning primitives. It never creates an Auth identity and never assigns
-- the role to a person during migration execution.

-- A stable id makes fresh resets deterministic. If a deployment already has a
-- role with this name, preserve its id and normalize only the role definition.
INSERT INTO "public"."roles" ("id", "name", "description", "is_active")
VALUES (
    '71200000-0000-0000-0000-000000000001'::uuid,
    'super_admin',
    'Platform-scoped administrator; does not imply tenant-role permissions.',
    true
)
ON CONFLICT ("name") DO UPDATE
SET "description" = EXCLUDED."description",
    "is_active" = true,
    "updated_at" = "now"();

-- A super_admin grant is valid only at platform scope. Existing tenant roles
-- retain their Phase 6.13 semantics; this guard does not widen any of them.
CREATE OR REPLACE FUNCTION "public"."phase712_assert_super_admin_scope"()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
    role_name text;
BEGIN
    SELECT "r"."name"
      INTO role_name
      FROM "public"."roles" AS "r"
     WHERE "r"."id" = NEW."role_id";

    IF role_name = 'super_admin'
       AND (
           NEW."scope_type" <> 'platform'
           OR NEW."scope_id" IS NOT NULL
           OR NEW."scope_organization_id" IS NOT NULL
       ) THEN
        RAISE EXCEPTION 'Phase 7.12: super_admin requires platform scope'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS "trg_phase712_super_admin_scope" ON "public"."user_roles";

CREATE TRIGGER "trg_phase712_super_admin_scope"
    BEFORE INSERT OR UPDATE OF "role_id", "scope_type", "scope_id", "scope_organization_id"
    ON "public"."user_roles"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."phase712_assert_super_admin_scope"();

-- Refuse to bless a pre-existing malformed grant. The migration does not
-- silently rewrite personal authorization data.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM "public"."user_roles" AS "ur"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
         WHERE "r"."name" = 'super_admin'
           AND (
               "ur"."scope_type" <> 'platform'
               OR "ur"."scope_id" IS NOT NULL
               OR "ur"."scope_organization_id" IS NOT NULL
           )
    ) THEN
        RAISE EXCEPTION 'Phase 7.12: an existing super_admin grant has non-platform scope';
    END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS "public"."platform_role_audit_log" (
    "audit_id" uuid DEFAULT "gen_random_uuid"() NOT NULL,
    "actor_identifier" text NOT NULL,
    "action" text NOT NULL,
    "target_user_id" uuid NOT NULL,
    "role_name" text NOT NULL,
    "result" text NOT NULL,
    "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
    "performed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "platform_role_audit_log_pkey" PRIMARY KEY ("audit_id"),
    CONSTRAINT "platform_role_audit_log_actor_check"
        CHECK ("btrim"("actor_identifier") <> '' AND "length"("actor_identifier") <= 200),
    CONSTRAINT "platform_role_audit_log_action_check"
        CHECK ("action" = ANY (ARRAY['assign'::text, 'revoke'::text])),
    CONSTRAINT "platform_role_audit_log_role_check"
        CHECK ("role_name" = 'super_admin'::text),
    CONSTRAINT "platform_role_audit_log_result_check"
        CHECK ("result" = ANY (ARRAY[
            'assigned'::text,
            'already_assigned'::text,
            'revoked'::text,
            'already_revoked'::text
        ])),
    CONSTRAINT "platform_role_audit_log_target_fkey"
        FOREIGN KEY ("target_user_id") REFERENCES "public"."users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "idx_platform_role_audit_target_time"
    ON "public"."platform_role_audit_log" ("target_user_id", "performed_at" DESC);

COMMENT ON TABLE "public"."platform_role_audit_log" IS
    'Phase 7.12 audit ledger for controlled super_admin assignment and revocation.';

REVOKE ALL ON TABLE "public"."platform_role_audit_log" FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT ON TABLE "public"."platform_role_audit_log" TO "service_role";

-- Internal service-role operation used by the explicitly local provisioning
-- wrapper. It is idempotent on user_roles(user_id, role_id).
CREATE OR REPLACE FUNCTION "public"."phase712_assign_super_admin"(
    "p_target_email" text,
    "p_actor_identifier" text
)
RETURNS TABLE ("result" text, "target_user_id" uuid)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    target_record "public"."users"%ROWTYPE;
    super_admin_role "public"."roles"%ROWTYPE;
    grant_exists boolean;
    operation_result text;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.12: service role required' USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF "btrim"(COALESCE("p_actor_identifier", '')) = ''
       OR "length"("p_actor_identifier") > 200 THEN
        RAISE EXCEPTION 'Phase 7.12: a bounded actor identifier is required'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO target_record
      FROM "public"."users"
     WHERE "email" = "lower"("btrim"("p_target_email"));
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: target application user not found'
            USING ERRCODE = 'no_data_found';
    END IF;
    IF target_record."status" <> 'active' THEN
        RAISE EXCEPTION 'Phase 7.12: target application user is not active'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO super_admin_role
      FROM "public"."roles"
     WHERE "name" = 'super_admin' AND "is_active" = true;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: active super_admin role is unavailable'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM "public"."user_roles"
         WHERE "user_id" = target_record."id"
           AND "role_id" = super_admin_role."id"
    ) INTO grant_exists;

    INSERT INTO "public"."user_roles" (
        "user_id", "role_id", "scope_type", "scope_id", "scope_organization_id"
    ) VALUES (
        target_record."id", super_admin_role."id", 'platform', NULL, NULL
    )
    ON CONFLICT ("user_id", "role_id") DO UPDATE
       SET "scope_type" = 'platform',
           "scope_id" = NULL,
           "scope_organization_id" = NULL;

    operation_result := CASE WHEN grant_exists THEN 'already_assigned' ELSE 'assigned' END;
    INSERT INTO "public"."platform_role_audit_log" (
        "actor_identifier", "action", "target_user_id", "role_name", "result", "metadata"
    ) VALUES (
        "btrim"("p_actor_identifier"), 'assign', target_record."id", 'super_admin',
        operation_result, '{"scope":"platform"}'::jsonb
    );

    RETURN QUERY SELECT operation_result, target_record."id";
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase712_revoke_super_admin"(
    "p_target_email" text,
    "p_actor_identifier" text
)
RETURNS TABLE ("result" text, "target_user_id" uuid)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    target_record "public"."users"%ROWTYPE;
    super_admin_role_id uuid;
    removed_count integer;
    operation_result text;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.12: service role required' USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF "btrim"(COALESCE("p_actor_identifier", '')) = ''
       OR "length"("p_actor_identifier") > 200 THEN
        RAISE EXCEPTION 'Phase 7.12: a bounded actor identifier is required'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT * INTO target_record
      FROM "public"."users"
     WHERE "email" = "lower"("btrim"("p_target_email"));
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: target application user not found'
            USING ERRCODE = 'no_data_found';
    END IF;

    SELECT "id" INTO super_admin_role_id
      FROM "public"."roles"
     WHERE "name" = 'super_admin';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Phase 7.12: super_admin role is unavailable'
            USING ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    DELETE FROM "public"."user_roles"
     WHERE "user_id" = target_record."id"
       AND "role_id" = super_admin_role_id;
    GET DIAGNOSTICS removed_count = ROW_COUNT;

    operation_result := CASE WHEN removed_count = 1 THEN 'revoked' ELSE 'already_revoked' END;
    INSERT INTO "public"."platform_role_audit_log" (
        "actor_identifier", "action", "target_user_id", "role_name", "result", "metadata"
    ) VALUES (
        "btrim"("p_actor_identifier"), 'revoke', target_record."id", 'super_admin',
        operation_result, '{"scope":"platform"}'::jsonb
    );

    RETURN QUERY SELECT operation_result, target_record."id";
END;
$$;

REVOKE ALL ON FUNCTION "public"."phase712_assign_super_admin"(text, text)
    FROM PUBLIC, "anon", "authenticated";
REVOKE ALL ON FUNCTION "public"."phase712_revoke_super_admin"(text, text)
    FROM PUBLIC, "anon", "authenticated";
GRANT EXECUTE ON FUNCTION "public"."phase712_assign_super_admin"(text, text) TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase712_revoke_super_admin"(text, text) TO "service_role";


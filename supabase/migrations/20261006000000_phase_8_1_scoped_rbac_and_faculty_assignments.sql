-- Phase 8.1: institution-scoped Staff permission grants and Faculty section
-- assignments. Existing roles, permissions, user_roles, and audit ledgers are
-- reused; global role_permissions are not writable by tenant administrators.

INSERT INTO "public"."permissions" ("name", "description", "code", "scope")
VALUES
    ('notifications.own.read', 'Read the caller''s own notifications.', 'notifications.own.read', 'user'),
    ('notifications.own.update', 'Update read state of the caller''s own notifications.', 'notifications.own.update', 'user'),
    ('organizations.manage', 'Decide institution join requests in the actor organization.', 'organizations.manage', 'organization'),
    ('faculty.assignments.read', 'Read own or institution-scoped Faculty section assignments.', 'faculty.assignments.read', 'institution'),
    ('faculty.assignments.manage', 'Manage Faculty section assignments in the institution.', 'faculty.assignments.manage', 'institution')
ON CONFLICT ("code") DO UPDATE
SET "name" = EXCLUDED."name",
    "description" = EXCLUDED."description",
    "scope" = EXCLUDED."scope",
    "is_active" = true,
    "updated_at" = "now"();

INSERT INTO "public"."role_permissions" ("role_id", "permission_id")
SELECT "role"."id", "permission"."id"
  FROM (VALUES
    ('super_admin', 'organizations.manage'),
    ('student', 'notifications.own.read'),
    ('student', 'notifications.own.update'),
    ('faculty', 'notifications.own.read'),
    ('faculty', 'notifications.own.update'),
    ('staff', 'notifications.own.read'),
    ('staff', 'notifications.own.update'),
    ('admin', 'organizations.manage'),
    ('admin', 'platform.manage'),
    ('admin', 'faculty.assignments.manage'),
    ('faculty', 'faculty.assignments.read')
  ) AS "grants"("role_name", "permission_code")
  JOIN "public"."roles" AS "role"
    ON "role"."name" = "grants"."role_name" AND "role"."is_active" = true
  JOIN "public"."permissions" AS "permission"
    ON "permission"."code" = "grants"."permission_code"
   AND "permission"."is_active" = true
ON CONFLICT ("role_id", "permission_id") DO NOTHING;

ALTER TABLE "public"."admin_audit_log"
    ADD COLUMN IF NOT EXISTS "institution_id" uuid
    REFERENCES "public"."institutions" ("institution_id") ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS "idx_admin_audit_log_institution_time"
    ON "public"."admin_audit_log" ("institution_id", "performed_at" DESC);

CREATE TABLE IF NOT EXISTS "public"."user_permission_grants" (
    "grant_id" uuid DEFAULT "gen_random_uuid"() PRIMARY KEY,
    "user_id" uuid NOT NULL REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "institution_id" uuid NOT NULL REFERENCES "public"."institutions" ("institution_id") ON DELETE RESTRICT,
    "permission_id" uuid NOT NULL REFERENCES "public"."permissions" ("id") ON DELETE RESTRICT,
    "granted_by" uuid NOT NULL REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "granted_at" timestamptz NOT NULL DEFAULT "now"(),
    "revoked_by" uuid REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "revoked_at" timestamptz,
    CONSTRAINT "user_permission_grants_revocation_pair_check"
        CHECK (("revoked_by" IS NULL) = ("revoked_at" IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS "uq_user_permission_grants_active"
    ON "public"."user_permission_grants" ("user_id", "institution_id", "permission_id")
    WHERE "revoked_at" IS NULL;
CREATE INDEX IF NOT EXISTS "idx_user_permission_grants_user_institution"
    ON "public"."user_permission_grants" ("user_id", "institution_id")
    WHERE "revoked_at" IS NULL;

CREATE TABLE IF NOT EXISTS "public"."faculty_section_assignments" (
    "assignment_id" uuid DEFAULT "gen_random_uuid"() PRIMARY KEY,
    "institution_id" uuid NOT NULL REFERENCES "public"."institutions" ("institution_id") ON DELETE RESTRICT,
    "faculty_user_id" uuid NOT NULL,
    "section_id" uuid NOT NULL REFERENCES "public"."sections" ("section_id") ON DELETE RESTRICT,
    "assigned_by" uuid NOT NULL,
    "assigned_at" timestamptz NOT NULL DEFAULT "now"(),
    "revoked_by" uuid REFERENCES "public"."users" ("id") ON DELETE RESTRICT,
    "revoked_at" timestamptz,
    CONSTRAINT "faculty_section_assignments_revocation_pair_check"
        CHECK (("revoked_by" IS NULL) = ("revoked_at" IS NULL))
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM "pg_catalog"."pg_constraint"
         WHERE "conname" = 'faculty_section_assignments_faculty_user_id_fkey'
           AND "conrelid" = '"public"."faculty_section_assignments"'::"regclass"
    ) THEN
        ALTER TABLE "public"."faculty_section_assignments"
            ADD CONSTRAINT "faculty_section_assignments_faculty_user_id_fkey"
            FOREIGN KEY ("faculty_user_id")
            REFERENCES "public"."users" ("id") ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "pg_catalog"."pg_constraint"
         WHERE "conname" = 'faculty_section_assignments_assigned_by_fkey'
           AND "conrelid" = '"public"."faculty_section_assignments"'::"regclass"
    ) THEN
        ALTER TABLE "public"."faculty_section_assignments"
            ADD CONSTRAINT "faculty_section_assignments_assigned_by_fkey"
            FOREIGN KEY ("assigned_by")
            REFERENCES "public"."users" ("id") ON DELETE RESTRICT;
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS "uq_faculty_section_assignments_active"
    ON "public"."faculty_section_assignments" ("faculty_user_id", "section_id")
    WHERE "revoked_at" IS NULL;
CREATE INDEX IF NOT EXISTS "idx_faculty_section_assignments_institution_section"
    ON "public"."faculty_section_assignments" ("institution_id", "section_id")
    WHERE "revoked_at" IS NULL;
CREATE INDEX IF NOT EXISTS "idx_faculty_section_assignments_faculty"
    ON "public"."faculty_section_assignments" ("faculty_user_id", "institution_id")
    WHERE "revoked_at" IS NULL;

ALTER TABLE "public"."user_permission_grants" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "public"."faculty_section_assignments" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "public"."user_permission_grants",
    "public"."faculty_section_assignments" FROM PUBLIC, "anon", "authenticated";
GRANT SELECT, INSERT, UPDATE ON TABLE "public"."user_permission_grants",
    "public"."faculty_section_assignments" TO "service_role";
GRANT INSERT ON TABLE "public"."admin_audit_log" TO "service_role";

COMMENT ON TABLE "public"."user_permission_grants" IS
    'Phase 8.1 additive, institution-scoped direct permissions for eligible Staff only; revocations retain history.';
COMMENT ON TABLE "public"."faculty_section_assignments" IS
    'Phase 8.1 active Faculty-to-section assignments; institution is validated against the offering department.';
COMMENT ON COLUMN "public"."admin_audit_log"."institution_id" IS
    'Tenant scope for institution audit events; NULL is reserved for platform/global events.';

CREATE OR REPLACE FUNCTION "public"."phase81_assert_institution_admin"(
    "p_actor_user_id" uuid,
    "p_institution_id" uuid
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 8.1: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."users" AS "actor"
          JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "actor"."id"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
          JOIN "public"."institutions" AS "i" ON "i"."institution_id" = "p_institution_id"
         WHERE "actor"."id" = "p_actor_user_id"
           AND "actor"."status" = 'active'
           AND "r"."name" = 'admin'
           AND "r"."is_active" = true
           AND "ur"."scope_type" = 'institution'
           AND "ur"."scope_id" = "p_institution_id"
           AND "i"."status" = 'active'
           AND "i"."is_active" = true
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active institution administrator required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase81_manage_staff_permission_grants"(
    "p_actor_user_id" uuid,
    "p_institution_id" uuid,
    "p_target_user_id" uuid,
    "p_permission_codes" text[],
    "p_grant" boolean
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    "permission_code" text;
    "permission_row" "public"."permissions"%ROWTYPE;
    "changed_count" integer := 0;
    "grant_id" uuid;
BEGIN
    PERFORM "public"."phase81_assert_institution_admin"(
        "p_actor_user_id", "p_institution_id"
    );
    IF "p_actor_user_id" = "p_target_user_id" THEN
        RAISE EXCEPTION 'Phase 8.1: administrators cannot grant Staff permissions to themselves'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."users" AS "target"
          JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "target"."id"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
         WHERE "target"."id" = "p_target_user_id"
           AND "target"."status" = 'active'
           AND "r"."name" = 'staff'
           AND "r"."is_active" = true
           AND "ur"."scope_type" = 'institution'
           AND "ur"."scope_id" = "p_institution_id"
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active Staff member in the institution required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF COALESCE("array_length"("p_permission_codes", 1), 0) = 0
       OR "array_length"("p_permission_codes", 1) > 32 THEN
        RAISE EXCEPTION 'Phase 8.1: permission list must contain 1 to 32 entries'
            USING ERRCODE = 'check_violation';
    END IF;
    IF "array_length"("p_permission_codes", 1) <>
       (SELECT "count"(DISTINCT "code") FROM "unnest"("p_permission_codes") AS "codes"("code")) THEN
        RAISE EXCEPTION 'Phase 8.1: duplicate permission codes are not accepted'
            USING ERRCODE = 'check_violation';
    END IF;

    FOREACH "permission_code" IN ARRAY "p_permission_codes"
    LOOP
        IF "permission_code" <> ALL (ARRAY[
            'ai.knowledge.create', 'attendance.read', 'attendance.manage',
            'results.read', 'results.manage', 'students.read', 'students.update',
            'documents.read', 'documents.create', 'documents.update',
            'notices.read', 'notices.create', 'notices.update'
        ]::text[]) THEN
            RAISE EXCEPTION 'Phase 8.1: permission is outside the Staff delegation allowlist'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        SELECT * INTO "permission_row"
          FROM "public"."permissions"
         WHERE "code" = "permission_code";
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Phase 8.1: unknown or inactive permission'
                USING ERRCODE = 'check_violation';
        END IF;
        IF "p_grant" AND NOT "permission_row"."is_active" THEN
            RAISE EXCEPTION 'Phase 8.1: unknown or inactive permission'
                USING ERRCODE = 'check_violation';
        END IF;

        IF "p_grant" THEN
            INSERT INTO "public"."user_permission_grants"
                ("user_id", "institution_id", "permission_id", "granted_by")
            VALUES
                ("p_target_user_id", "p_institution_id", "permission_row"."id", "p_actor_user_id")
            ON CONFLICT ("user_id", "institution_id", "permission_id")
                WHERE "revoked_at" IS NULL DO NOTHING
            RETURNING "user_permission_grants"."grant_id" INTO "grant_id";
            IF "grant_id" IS NOT NULL THEN
                INSERT INTO "public"."admin_audit_log"
                    ("actor_user_id", "institution_id", "action", "table_name",
                     "record_id", "record_data", "status")
                VALUES
                    ("p_actor_user_id", "p_institution_id", 'permission.grant',
                     'user_permission_grants', "grant_id"::text,
                     "jsonb_build_object"('target_user_id', "p_target_user_id",
                         'permission_code', "permission_code", 'source', 'direct'),
                     'success');
                "changed_count" := "changed_count" + 1;
            END IF;
            "grant_id" := NULL;
        ELSE
            UPDATE "public"."user_permission_grants"
               SET "revoked_by" = "p_actor_user_id", "revoked_at" = "now"()
             WHERE "user_id" = "p_target_user_id"
               AND "institution_id" = "p_institution_id"
               AND "permission_id" = "permission_row"."id"
               AND "revoked_at" IS NULL
            RETURNING "grant_id" INTO "grant_id";
            IF "grant_id" IS NOT NULL THEN
                INSERT INTO "public"."admin_audit_log"
                    ("actor_user_id", "institution_id", "action", "table_name",
                     "record_id", "record_data", "status")
                VALUES
                    ("p_actor_user_id", "p_institution_id", 'permission.revoke',
                     'user_permission_grants', "grant_id"::text,
                     "jsonb_build_object"('target_user_id', "p_target_user_id",
                         'permission_code', "permission_code", 'source', 'direct'),
                     'success');
                "changed_count" := "changed_count" + 1;
            END IF;
            "grant_id" := NULL;
        END IF;
    END LOOP;
    RETURN "changed_count";
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase81_manage_faculty_section_assignment"(
    "p_actor_user_id" uuid,
    "p_institution_id" uuid,
    "p_faculty_user_id" uuid,
    "p_section_id" uuid,
    "p_revoke" boolean DEFAULT false
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    "assignment_id" uuid;
BEGIN
    PERFORM "public"."phase81_assert_institution_admin"(
        "p_actor_user_id", "p_institution_id"
    );
    IF NOT "p_revoke" THEN
        IF NOT EXISTS (
            SELECT 1
              FROM "public"."users" AS "faculty"
              JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "faculty"."id"
              JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
             WHERE "faculty"."id" = "p_faculty_user_id"
               AND "faculty"."status" = 'active'
               AND "r"."name" = 'faculty'
               AND "r"."is_active" = true
               AND "ur"."scope_type" = 'institution'
               AND "ur"."scope_id" = "p_institution_id"
        ) THEN
            RAISE EXCEPTION 'Phase 8.1: active Faculty member in the institution required'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF NOT EXISTS (
            SELECT 1
              FROM "public"."sections" AS "section"
              JOIN "public"."course_offerings" AS "offering"
                ON "offering"."course_offering_id" = "section"."course_offering_id"
              JOIN "public"."courses" AS "course" ON "course"."course_id" = "offering"."course_id"
              JOIN "public"."departments" AS "department"
                ON "department"."department_id" = "course"."department_id"
             WHERE "section"."section_id" = "p_section_id"
               AND "section"."is_active" = true
               AND "offering"."is_active" = true
               AND "course"."is_active" = true
               AND "department"."is_active" = true
               AND "department"."institution_id" = "p_institution_id"
        ) THEN
            RAISE EXCEPTION 'Phase 8.1: active section in the institution required'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;

    IF "p_revoke" THEN
        UPDATE "public"."faculty_section_assignments"
           SET "revoked_by" = "p_actor_user_id", "revoked_at" = "now"()
         WHERE "faculty_user_id" = "p_faculty_user_id"
           AND "institution_id" = "p_institution_id"
           AND "section_id" = "p_section_id"
           AND "revoked_at" IS NULL
        RETURNING "faculty_section_assignments"."assignment_id" INTO "assignment_id";
        IF "assignment_id" IS NOT NULL THEN
            INSERT INTO "public"."admin_audit_log"
                ("actor_user_id", "institution_id", "action", "table_name",
                 "record_id", "record_data", "status")
            VALUES
                ("p_actor_user_id", "p_institution_id", 'faculty.assignment.revoke',
                 'faculty_section_assignments', "assignment_id"::text,
                 "jsonb_build_object"('faculty_user_id', "p_faculty_user_id",
                     'section_id', "p_section_id"), 'success');
        END IF;
        RETURN "assignment_id";
    END IF;

    INSERT INTO "public"."faculty_section_assignments"
        ("institution_id", "faculty_user_id", "section_id", "assigned_by")
    VALUES ("p_institution_id", "p_faculty_user_id", "p_section_id", "p_actor_user_id")
    ON CONFLICT ("faculty_user_id", "section_id") WHERE "revoked_at" IS NULL DO NOTHING
    RETURNING "faculty_section_assignments"."assignment_id" INTO "assignment_id";
    IF "assignment_id" IS NOT NULL THEN
        INSERT INTO "public"."admin_audit_log"
            ("actor_user_id", "institution_id", "action", "table_name",
             "record_id", "record_data", "status")
        VALUES
            ("p_actor_user_id", "p_institution_id", 'faculty.assignment.assign',
             'faculty_section_assignments', "assignment_id"::text,
             "jsonb_build_object"('faculty_user_id', "p_faculty_user_id",
                 'section_id', "p_section_id"), 'success');
    ELSE
        SELECT "assignment"."assignment_id" INTO "assignment_id"
          FROM "public"."faculty_section_assignments" AS "assignment"
         WHERE "assignment"."faculty_user_id" = "p_faculty_user_id"
           AND "assignment"."section_id" = "p_section_id"
           AND "assignment"."revoked_at" IS NULL;
    END IF;
    RETURN "assignment_id";
END;
$$;

CREATE OR REPLACE FUNCTION "public"."phase81_assign_institution_role_audited"(
    "p_actor_user_id" uuid,
    "p_target_user_id" uuid,
    "p_institution_id" uuid,
    "p_role_name" text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    "role_id" uuid;
    "organization_id" uuid;
    "previous_scope_type" text;
    "previous_scope_id" uuid;
    "changed" boolean := false;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 8.1: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF "p_role_name" NOT IN ('admin', 'staff', 'faculty') THEN
        RAISE EXCEPTION 'Phase 8.1: unsupported institution role'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "public"."users"
         WHERE "id" = "p_target_user_id" AND "status" = 'active'
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active target account required'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM "public"."institutions"
         WHERE "institution_id" = "p_institution_id"
           AND "status" = 'active' AND "is_active" = true
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: active institution required'
            USING ERRCODE = 'check_violation';
    END IF;
    IF "p_actor_user_id" <> "p_target_user_id" AND NOT EXISTS (
        SELECT 1
          FROM "public"."users" AS "actor"
          JOIN "public"."user_roles" AS "ur" ON "ur"."user_id" = "actor"."id"
          JOIN "public"."roles" AS "r" ON "r"."id" = "ur"."role_id"
         WHERE "actor"."id" = "p_actor_user_id"
           AND "actor"."status" = 'active'
           AND "r"."name" = 'super_admin' AND "r"."is_active" = true
           AND "ur"."scope_type" = 'platform'
           AND "ur"."scope_id" IS NULL
           AND "ur"."scope_organization_id" IS NULL
    ) THEN
        RAISE EXCEPTION 'Phase 8.1: target acceptance or active platform administrator required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT "institution"."organization_id" INTO "organization_id"
      FROM "public"."institutions" AS "institution"
     WHERE "institution"."institution_id" = "p_institution_id";
    SELECT "id" INTO "role_id"
      FROM "public"."roles"
     WHERE "name" = "p_role_name" AND "is_active" = true;
    IF "role_id" IS NULL OR "organization_id" IS NULL THEN
        RAISE EXCEPTION 'Phase 8.1: role or organization scope is not configured'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT "ur"."scope_type", "ur"."scope_id"
      INTO "previous_scope_type", "previous_scope_id"
      FROM "public"."user_roles" AS "ur"
     WHERE "ur"."user_id" = "p_target_user_id" AND "ur"."role_id" = "role_id"
     FOR UPDATE;
    "changed" := NOT FOUND OR "previous_scope_type" IS DISTINCT FROM 'institution'
        OR "previous_scope_id" IS DISTINCT FROM "p_institution_id";

    INSERT INTO "public"."user_roles"
        ("user_id", "role_id", "scope_type", "scope_id", "scope_organization_id")
    VALUES
        ("p_target_user_id", "role_id", 'institution', "p_institution_id", "organization_id")
    ON CONFLICT ("user_id", "role_id") DO UPDATE
        SET "scope_type" = EXCLUDED."scope_type",
            "scope_id" = EXCLUDED."scope_id",
            "scope_organization_id" = EXCLUDED."scope_organization_id";

    IF "changed" THEN
        INSERT INTO "public"."admin_audit_log"
            ("actor_user_id", "institution_id", "action", "table_name",
             "record_id", "record_data", "status")
        VALUES
            ("p_actor_user_id", "p_institution_id", 'role.assignment',
             'user_roles', "p_target_user_id"::text,
             "jsonb_build_object"('role', "p_role_name",
                 'institution_id', "p_institution_id"), 'success');
    END IF;
    RETURN "changed";
END;
$$;

GRANT EXECUTE ON FUNCTION "public"."phase81_assert_institution_admin"(uuid, uuid)
    TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase81_manage_staff_permission_grants"(uuid, uuid, uuid, text[], boolean)
    TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase81_manage_faculty_section_assignment"(uuid, uuid, uuid, uuid, boolean)
    TO "service_role";
GRANT EXECUTE ON FUNCTION "public"."phase81_assign_institution_role_audited"(uuid, uuid, uuid, text)
    TO "service_role";
REVOKE ALL ON FUNCTION "public"."phase81_assert_institution_admin"(uuid, uuid)
    FROM PUBLIC, "anon", "authenticated";
REVOKE ALL ON FUNCTION "public"."phase81_manage_staff_permission_grants"(uuid, uuid, uuid, text[], boolean)
    FROM PUBLIC, "anon", "authenticated";
REVOKE ALL ON FUNCTION "public"."phase81_manage_faculty_section_assignment"(uuid, uuid, uuid, uuid, boolean)
    FROM PUBLIC, "anon", "authenticated";
REVOKE ALL ON FUNCTION "public"."phase81_assign_institution_role_audited"(uuid, uuid, uuid, text)
    FROM PUBLIC, "anon", "authenticated";

CREATE OR REPLACE FUNCTION "public"."phase81_prevent_audit_mutation"()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION 'Audit records are append-only'
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

DROP TRIGGER IF EXISTS "phase81_admin_audit_append_only" ON "public"."admin_audit_log";
CREATE TRIGGER "phase81_admin_audit_append_only"
    BEFORE UPDATE OR DELETE ON "public"."admin_audit_log"
    FOR EACH ROW EXECUTE FUNCTION "public"."phase81_prevent_audit_mutation"();

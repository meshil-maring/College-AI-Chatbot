-- Phase 7.24: approving a Staff/Faculty request grants its institution-scoped
-- role in the same transaction. Approved applicants can use their existing
-- credentials without accepting a separate invitation.

CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_and_grant_role"(
    "p_request_id" uuid,
    "p_institution_id" uuid,
    "p_decided_by" uuid,
    "p_reason" text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    "v_request" "public"."institution_membership_requests"%ROWTYPE;
    "v_role_id" uuid;
    "v_previous_scope_type" text;
    "v_previous_scope_id" uuid;
    "v_changed" boolean := false;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.24: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT * INTO "v_request"
      FROM "public"."institution_membership_requests"
     WHERE "request_id" = "p_request_id"
       AND "institution_id" = "p_institution_id"
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN "jsonb_build_object"('not_found', true);
    END IF;
    IF "v_request"."status" = 'approved'::text THEN
        RETURN "jsonb_build_object"('already_applied', true);
    END IF;
    IF "v_request"."status" <> 'pending'::text THEN
        RETURN "jsonb_build_object"('conflict', true);
    END IF;
    IF "v_request"."requested_role" NOT IN ('staff', 'faculty') THEN
        RETURN "jsonb_build_object"('invalid_role', true);
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."institutions" AS "institution"
          JOIN "public"."users" AS "applicant"
            ON "applicant"."id" = "v_request"."user_id"
         WHERE "institution"."institution_id" = "p_institution_id"
           AND "institution"."organization_id" = "v_request"."organization_id"
           AND "institution"."status" = 'active'::text
           AND "institution"."is_active" = true
           AND "lower"("applicant"."email") = "lower"("v_request"."official_email")
           AND "applicant"."status" = 'active'::text
    ) THEN
        RETURN "jsonb_build_object"('invalid_state', true);
    END IF;

    PERFORM "public"."phase81_assert_institution_admin"(
        "p_decided_by", "p_institution_id"
    );

    SELECT "id" INTO "v_role_id"
      FROM "public"."roles"
     WHERE "name" = "v_request"."requested_role"
       AND "is_active" = true;
    IF "v_role_id" IS NULL THEN
        RETURN "jsonb_build_object"('role_not_configured', true);
    END IF;

    SELECT "scope_type", "scope_id"
      INTO "v_previous_scope_type", "v_previous_scope_id"
      FROM "public"."user_roles"
     WHERE "user_id" = "v_request"."user_id"
       AND "role_id" = "v_role_id"
     FOR UPDATE;
    "v_changed" := NOT FOUND
        OR "v_previous_scope_type" IS DISTINCT FROM 'institution'
        OR "v_previous_scope_id" IS DISTINCT FROM "p_institution_id";

    INSERT INTO "public"."user_roles" (
        "user_id", "role_id", "scope_type", "scope_id", "scope_organization_id"
    ) VALUES (
        "v_request"."user_id", "v_role_id", 'institution'::text,
        "p_institution_id", "v_request"."organization_id"
    )
    ON CONFLICT ("user_id", "role_id") DO UPDATE
        SET "scope_type" = EXCLUDED."scope_type",
            "scope_id" = EXCLUDED."scope_id",
            "scope_organization_id" = EXCLUDED."scope_organization_id";

    IF "v_changed" THEN
        INSERT INTO "public"."admin_audit_log" (
            "actor_user_id", "institution_id", "action", "table_name",
            "record_id", "record_data", "status"
        ) VALUES (
            "p_decided_by", "p_institution_id", 'role.assignment',
            'user_roles', "v_request"."user_id"::text,
            "jsonb_build_object"(
                'role', "v_request"."requested_role",
                'institution_id', "p_institution_id",
                'membership_request_id', "p_request_id"
            ),
            'success'
        );
    END IF;

    UPDATE "public"."institution_membership_requests"
       SET "status" = 'approved'::text,
           "decided_by_user_id" = "p_decided_by",
           "decided_at" = "now"(),
           "decision_reason" = "p_reason",
           "updated_at" = "now"()
     WHERE "request_id" = "p_request_id";

    RETURN "jsonb_build_object"(
        'already_applied', false,
        'role_granted', true
    );
END;
$$;

REVOKE ALL ON FUNCTION "public"."phase723_approve_membership_and_grant_role"(
    uuid, uuid, uuid, text
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION "public"."phase723_approve_membership_and_grant_role"(
    uuid, uuid, uuid, text
) TO service_role;

-- Apply the new rule to already-approved, still-active applicants as well.
-- Never move an existing Staff/Faculty grant to a different institution.
WITH "candidates" AS (
    SELECT DISTINCT ON ("request"."user_id", "role"."id")
           "request"."user_id",
           "request"."institution_id",
           "request"."organization_id",
           "request"."requested_role",
           "request"."request_id",
           "request"."decided_by_user_id",
           "role"."id" AS "role_id"
      FROM "public"."institution_membership_requests" AS "request"
      JOIN "public"."institutions" AS "institution"
        ON "institution"."institution_id" = "request"."institution_id"
       AND "institution"."organization_id" = "request"."organization_id"
       AND "institution"."status" = 'active'::text
       AND "institution"."is_active" = true
      JOIN "public"."users" AS "applicant"
        ON "applicant"."id" = "request"."user_id"
       AND "lower"("applicant"."email") = "lower"("request"."official_email")
       AND "applicant"."status" = 'active'::text
      JOIN "public"."roles" AS "role"
        ON "role"."name" = "request"."requested_role"
       AND "role"."is_active" = true
     WHERE "request"."status" = 'approved'::text
       AND "request"."requested_role" IN ('staff', 'faculty')
       AND "request"."decided_by_user_id" IS NOT NULL
     ORDER BY "request"."user_id", "role"."id",
              "request"."decided_at" DESC NULLS LAST,
              "request"."created_at" DESC
),
"eligible" AS (
    SELECT "candidate".*
      FROM "candidates" AS "candidate"
     WHERE NOT EXISTS (
         SELECT 1
           FROM "public"."institution_membership_requests" AS "other_request"
          WHERE "other_request"."user_id" = "candidate"."user_id"
            AND "other_request"."status" = 'approved'::text
            AND "other_request"."requested_role" = "candidate"."requested_role"
            AND "other_request"."institution_id" <> "candidate"."institution_id"
     )
       AND NOT EXISTS (
         SELECT 1
           FROM "public"."user_roles" AS "existing_grant"
          WHERE "existing_grant"."user_id" = "candidate"."user_id"
            AND "existing_grant"."role_id" = "candidate"."role_id"
            AND (
                "existing_grant"."scope_type" <> 'institution'::text
                OR "existing_grant"."scope_id" <> "candidate"."institution_id"
            )
     )
),
"granted" AS (
    INSERT INTO "public"."user_roles" (
        "user_id", "role_id", "scope_type", "scope_id", "scope_organization_id"
    )
    SELECT "eligible"."user_id", "eligible"."role_id", 'institution'::text,
           "eligible"."institution_id", "eligible"."organization_id"
      FROM "eligible"
    ON CONFLICT ("user_id", "role_id") DO NOTHING
    RETURNING "user_id", "role_id"
)
INSERT INTO "public"."admin_audit_log" (
    "actor_user_id", "institution_id", "action", "table_name",
    "record_id", "record_data", "status"
)
SELECT "eligible"."decided_by_user_id",
       "eligible"."institution_id",
       'role.assignment',
       'user_roles',
       "eligible"."user_id"::text,
       "jsonb_build_object"(
           'role', "eligible"."requested_role",
           'institution_id', "eligible"."institution_id",
           'membership_request_id', "eligible"."request_id",
           'grant_reason', 'approved_membership_backfill'
       ),
       'success'
  FROM "granted"
  JOIN "eligible"
    ON "eligible"."user_id" = "granted"."user_id"
   AND "eligible"."role_id" = "granted"."role_id";

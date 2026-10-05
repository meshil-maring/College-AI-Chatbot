-- Phase 8 — granular permissions on the existing RBAC schema.
--
-- Reuse permissions, role_permissions, roles, and user_roles. No direct-user
-- override is introduced. "admin" is the existing University Admin role name;
-- changing it would break the locked auth and frontend contracts.

INSERT INTO "public"."roles" ("name", "description", "is_active")
VALUES
    ('admin', 'Institution-scoped University Admin.', true),
    ('faculty', 'Institution-scoped faculty member.', true),
    ('staff', 'Institution-scoped staff member.', true),
    ('student', 'Institution-scoped student.', true)
ON CONFLICT ("name") DO NOTHING;

INSERT INTO "public"."permissions" ("name", "description", "code", "scope")
SELECT "permission"."code",
       "permission"."description",
       "permission"."code",
       'global'
  FROM (VALUES
    ('profile.own.read', 'Read the caller''s own profile.'),
    ('profile.own.update', 'Update the caller''s own profile.'),
    ('users.read', 'Read users within the authorized scope.'),
    ('users.create', 'Create users within the authorized scope.'),
    ('users.update', 'Update users within the authorized scope.'),
    ('users.delete', 'Delete users within the authorized scope.'),
    ('roles.read', 'Read role definitions and grants.'),
    ('roles.manage', 'Manage role definitions and grants.'),
    ('permissions.read', 'Read permission definitions and role grants.'),
    ('permissions.manage', 'Manage role permission grants.'),
    ('students.read', 'Read student records within the authorized scope.'),
    ('students.create', 'Create student records within the authorized scope.'),
    ('students.update', 'Update student records within the authorized scope.'),
    ('students.delete', 'Delete student records within the authorized scope.'),
    ('students.approve', 'Approve student registrations within the authorized scope.'),
    ('students.reject', 'Reject student registrations within the authorized scope.'),
    ('students.suspend', 'Suspend student access within the authorized scope.'),
    ('faculty.read', 'Read faculty records within the authorized scope.'),
    ('faculty.create', 'Create faculty records within the authorized scope.'),
    ('faculty.update', 'Update faculty records within the authorized scope.'),
    ('faculty.approve', 'Approve faculty registrations within the authorized scope.'),
    ('faculty.suspend', 'Suspend faculty access within the authorized scope.'),
    ('staff.read', 'Read staff records within the authorized scope.'),
    ('staff.create', 'Create staff records within the authorized scope.'),
    ('staff.update', 'Update staff records within the authorized scope.'),
    ('staff.approve', 'Approve staff registrations within the authorized scope.'),
    ('staff.suspend', 'Suspend staff access within the authorized scope.'),
    ('departments.read', 'Read departments within the authorized scope.'),
    ('departments.manage', 'Manage departments within the authorized scope.'),
    ('courses.read', 'Read courses within the authorized scope.'),
    ('courses.manage', 'Manage courses within the authorized scope.'),
    ('subjects.read', 'Read subjects within the authorized scope.'),
    ('subjects.manage', 'Manage subjects within the authorized scope.'),
    ('semesters.read', 'Read semesters within the authorized scope.'),
    ('semesters.manage', 'Manage semesters within the authorized scope.'),
    ('academic_years.read', 'Read academic years within the authorized scope.'),
    ('academic_years.manage', 'Manage academic years within the authorized scope.'),
    ('attendance.read', 'Read attendance within the authorized scope.'),
    ('attendance.manage', 'Manage attendance within the authorized scope.'),
    ('attendance.own.read', 'Read the caller''s own attendance.'),
    ('results.read', 'Read results within the authorized scope.'),
    ('results.manage', 'Manage results within the authorized scope.'),
    ('results.own.read', 'Read the caller''s own results.'),
    ('documents.read', 'Read documents within the authorized scope.'),
    ('documents.create', 'Create documents within the authorized scope.'),
    ('documents.update', 'Update documents within the authorized scope.'),
    ('documents.delete', 'Delete documents within the authorized scope.'),
    ('notices.read', 'Read notices available within the authorized scope.'),
    ('notices.create', 'Create notices within the authorized scope.'),
    ('notices.update', 'Update notices within the authorized scope.'),
    ('notices.delete', 'Delete notices within the authorized scope.'),
    ('ai.chat', 'Use authenticated AI chat.'),
    ('ai.knowledge.read', 'Read AI knowledge within the authorized scope.'),
    ('ai.knowledge.create', 'Create AI knowledge within the authorized scope.'),
    ('ai.knowledge.update', 'Update AI knowledge within the authorized scope.'),
    ('ai.knowledge.delete', 'Delete AI knowledge within the authorized scope.'),
    ('ai.configuration.manage', 'Manage AI configuration within the authorized scope.'),
    ('institution.read', 'Read the caller''s institution.'),
    ('institution.update', 'Update the caller''s institution.'),
    ('institution.settings.manage', 'Manage the caller''s institution settings.'),
    ('institutions.read', 'Read institutions across the platform.'),
    ('institutions.create', 'Create institutions across the platform.'),
    ('institutions.update', 'Update institutions across the platform.'),
    ('institutions.delete', 'Delete institutions across the platform.'),
    ('platform.read', 'Read platform-level administration data.'),
    ('platform.manage', 'Manage platform-level administration data.'),
    ('platform.settings.manage', 'Manage platform configuration.'),
    ('platform.audit.read', 'Read platform-level audit records.'),
    ('audit.read', 'Read audit records within the authorized scope.')
  ) AS "permission"("code", "description")
ON CONFLICT ("code") DO UPDATE
SET "description" = EXCLUDED."description",
    "is_active" = true,
    "updated_at" = "now"();

-- The default matrix is additive and idempotent. Existing explicit grants are
-- preserved; role_permissions remains the source of truth after provisioning.
WITH "role_grants"("role_name", "permission_codes") AS (
    VALUES
    ('super_admin', ARRAY[
        'profile.own.read', 'platform.read', 'platform.manage',
        'platform.settings.manage', 'platform.audit.read',
        'institutions.read', 'institutions.create', 'institutions.update',
        'institutions.delete', 'users.read', 'users.create', 'users.update',
        'users.delete', 'roles.read', 'roles.manage', 'permissions.read',
        'permissions.manage', 'audit.read'
    ]::text[]),
    ('admin', ARRAY[
        'profile.own.read', 'profile.own.update', 'institution.read',
        'institution.update', 'institution.settings.manage', 'users.read',
        'users.create', 'users.update', 'roles.read', 'roles.manage',
        'permissions.read', 'permissions.manage', 'students.read',
        'students.create', 'students.update', 'students.delete',
        'students.approve', 'students.reject', 'students.suspend',
        'faculty.read', 'faculty.create', 'faculty.update', 'faculty.approve',
        'faculty.suspend', 'staff.read', 'staff.create', 'staff.update',
        'staff.approve', 'staff.suspend', 'departments.read',
        'departments.manage', 'courses.read', 'courses.manage',
        'subjects.read', 'subjects.manage', 'semesters.read',
        'semesters.manage', 'academic_years.read', 'academic_years.manage',
        'attendance.read', 'attendance.manage', 'results.read', 'results.manage',
        'documents.read', 'documents.create', 'documents.update',
        'documents.delete', 'notices.read', 'notices.create', 'notices.update',
        'notices.delete', 'ai.chat', 'ai.knowledge.read', 'ai.knowledge.create',
        'ai.knowledge.update', 'ai.knowledge.delete', 'audit.read'
    ]::text[]),
    ('faculty', ARRAY[
        'profile.own.read', 'profile.own.update', 'ai.chat',
        'ai.knowledge.read', 'ai.knowledge.create', 'students.read', 'attendance.read',
        'attendance.manage', 'attendance.own.read', 'results.read',
        'results.manage', 'results.own.read', 'documents.read',
        'documents.create', 'notices.read'
    ]::text[]),
    ('staff', ARRAY[
        'profile.own.read', 'profile.own.update', 'ai.chat',
        'ai.knowledge.create', 'students.read',
        'students.update', 'students.approve', 'students.reject',
        'attendance.read', 'attendance.manage', 'results.read',
        'documents.read', 'documents.create', 'documents.update',
        'notices.read', 'notices.create', 'notices.update'
    ]::text[]),
    ('student', ARRAY[
        'profile.own.read', 'profile.own.update', 'ai.chat',
        'attendance.own.read', 'results.own.read', 'documents.read',
        'notices.read'
    ]::text[])
)
INSERT INTO "public"."role_permissions" ("role_id", "permission_id")
SELECT "role"."id", "permission"."id"
  FROM "role_grants"
 CROSS JOIN LATERAL "unnest"("role_grants"."permission_codes") AS "granted"("code")
  JOIN "public"."roles" AS "role"
    ON "role"."name" = "role_grants"."role_name"
   AND "role"."is_active" = true
  JOIN "public"."permissions" AS "permission"
    ON "permission"."code" = "granted"."code"
   AND "permission"."is_active" = true
ON CONFLICT ("role_id", "permission_id") DO NOTHING;

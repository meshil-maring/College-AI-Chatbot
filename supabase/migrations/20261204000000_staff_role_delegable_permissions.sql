-- Staff permissions become per-member choices. The Staff role keeps only its
-- baseline (own profile, notifications, AI chat, student approval decisions);
-- the delegable job-function permissions move to direct grants, which an
-- administrator can tick or untick for each Staff member.
--
-- Nobody loses access: every current Staff assignment first receives a direct
-- grant for each delegable permission the role gave it, and only then are
-- those permissions removed from the role. Each backfilled grant is attributed
-- to the institution Owner (or the member, where no Owner is recorded) and
-- audited. The delegable list matches phase81_manage_staff_permission_grants
-- (20261023000000) and DELEGABLE_STAFF_PERMISSIONS in the backend.
BEGIN;

CREATE TEMPORARY TABLE staff_delegable_codes (code text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO staff_delegable_codes (code) VALUES
    ('ai.knowledge.create'), ('students.read'), ('students.update'),
    ('documents.read'), ('documents.create'), ('documents.update'),
    ('notices.read'), ('notices.create'), ('notices.update');

WITH backfill AS (
    INSERT INTO public.user_permission_grants (user_id, institution_id, permission_id, granted_by)
    SELECT DISTINCT ur.user_id, ur.scope_id, p.permission_id, COALESCE(i.owner_user_id, ur.user_id)
    FROM public.user_roles ur
    JOIN public.roles r ON r.id = ur.role_id AND r.name = 'staff'
    JOIN public.institutions i ON i.institution_id = ur.scope_id
    JOIN public.role_permissions rp ON rp.role_id = r.id
    JOIN public.permissions p ON p.permission_id = rp.permission_id
    JOIN staff_delegable_codes c ON c.code = p.code
    WHERE ur.scope_type = 'institution'
    ON CONFLICT (user_id, institution_id, permission_id) WHERE revoked_at IS NULL DO NOTHING
    RETURNING grant_id, user_id, institution_id, permission_id, granted_by
)
INSERT INTO public.admin_audit_log
    (actor_user_id, institution_id, action, table_name, record_id, record_data, status)
SELECT b.granted_by, b.institution_id, 'permission.grant', 'user_permission_grants', b.grant_id::text,
       jsonb_build_object('target_user_id', b.user_id, 'permission_code', p.code,
                          'source', 'staff_role_migration'),
       'success'
FROM backfill b
JOIN public.permissions p ON p.permission_id = b.permission_id;

DELETE FROM public.role_permissions rp
USING public.roles r, public.permissions p, staff_delegable_codes c
WHERE rp.role_id = r.id AND r.name = 'staff'
  AND rp.permission_id = p.permission_id AND p.code = c.code;

COMMIT;

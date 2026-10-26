-- Only the four exact Stage 2 permissions; no staff delegation or wildcards.
INSERT INTO public.permissions (code, name, description, scope, is_active)
SELECT resource || '.' || operation, title || ' ' || operation,
       'Academic Setup: ' || title || ' ' || operation, 'institution', true
FROM (VALUES ('semesters', 'Study semesters'), ('subjects', 'Reusable subjects')) AS resources(resource, title)
CROSS JOIN (VALUES ('read'), ('manage')) AS operations(operation)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name, description = EXCLUDED.description,
    scope = EXCLUDED.scope, is_active = true, updated_at = now();

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.permission_id
FROM public.roles r CROSS JOIN public.permissions p
WHERE r.name = 'admin' AND p.code IN (
    'semesters.read', 'semesters.manage', 'subjects.read', 'subjects.manage'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

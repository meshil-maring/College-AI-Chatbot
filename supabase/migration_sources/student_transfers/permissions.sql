-- Students request and read their own transfers. Institution administrators
-- read and decide every transfer. Heads of Department receive no role grant:
-- their authority comes only from a current department_heads appointment.
INSERT INTO public.permissions (code, name, description, scope, is_active)
VALUES
    ('transfers.request', 'Request academic transfer',
        'Submit and cancel own section or program transfer requests', 'institution', true),
    ('transfers.read', 'Read academic transfers', 'View academic transfer requests', 'institution', true),
    ('transfers.approve', 'Decide academic transfers',
        'Review, approve and reject academic transfer requests', 'institution', true)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name, description = EXCLUDED.description,
    scope = 'institution', is_active = true, updated_at = now();

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.permission_id
FROM public.roles r CROSS JOIN public.permissions p
WHERE (r.name = 'student' AND p.code IN ('transfers.request', 'transfers.read'))
   OR (r.name = 'admin' AND p.code IN ('transfers.read', 'transfers.approve'))
ON CONFLICT (role_id, permission_id) DO NOTHING;

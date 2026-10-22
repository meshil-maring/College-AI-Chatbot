INSERT INTO public.permissions(name, code, description, scope)
SELECT code, code, description, 'institution' FROM (VALUES
    ('academic.curriculum.read','Read named curricula within the authorized institution.'),
    ('academic.curriculum.manage','Manage unused curriculum versions and fixed packages.'),
    ('academic.class.read','Read academic classes within the authorized scope.'),
    ('academic.class.manage','Configure academic classes, mappings and selection rules.'),
    ('academic.package.assign','Assign complete packages within an authorized class.'),
    ('academic.package.change','Change assigned packages before the class cutoff.'),
    ('academic.package.requests.review','Review package change requests within authorized scope.'),
    ('academic.package.own.read','Read the caller''s own package placement and history.'),
    ('academic.package.own.select','Choose an initial own-class package when enabled.'),
    ('academic.package.own.request','Request a package change before the class cutoff.')
) AS definitions(code, description) ON CONFLICT (code) DO NOTHING;
INSERT INTO public.role_permissions(role_id, permission_id)
SELECT r.id, p.permission_id FROM public.roles r CROSS JOIN public.permissions p
WHERE (r.name = 'admin' AND p.code IN ('academic.curriculum.read','academic.curriculum.manage',
    'academic.class.read','academic.class.manage','academic.package.assign','academic.package.change','academic.package.requests.review'))
    OR (r.name = 'student' AND p.code IN ('academic.package.own.read','academic.package.own.select','academic.package.own.request'))
ON CONFLICT DO NOTHING;
-- Staff receives only explicitly delegated capabilities; ordinary teachers
-- receive no global package permissions. Responsibilities remain scope-bound.
INSERT INTO public.responsibility_permissions(responsibility_code, permission_id)
SELECT rd.code, p.permission_id FROM public.responsibility_definitions rd CROSS JOIN public.permissions p
WHERE rd.code IN ('hod','class_in_charge') AND p.code IN ('academic.class.read',
    'academic.package.assign','academic.package.change','academic.package.requests.review') ON CONFLICT DO NOTHING;

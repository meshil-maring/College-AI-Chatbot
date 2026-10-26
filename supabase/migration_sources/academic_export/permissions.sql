-- Export resources: departments covers programs; courses covers curriculum,
-- offerings and sections. Restrict these grants to institutional admins.
INSERT INTO public.permissions (code, name, description, scope, is_active)
SELECT resource || '.' || operation, title || ' ' || operation,
       'Academic Setup: ' || title || ' ' || operation, 'institution', true
FROM (VALUES ('departments', 'Departments and programs'), ('courses', 'Courses and offerings'),
             ('academic_years', 'Academic years'), ('semesters', 'Semesters')) AS resources(resource, title)
CROSS JOIN (VALUES ('read'), ('manage')) AS operations(operation)
ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name, description=EXCLUDED.description,
    scope='institution', is_active=true, updated_at=now();

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.permission_id FROM public.roles r CROSS JOIN public.permissions p
WHERE r.name='admin' AND p.code IN (
    'departments.read','departments.manage','courses.read','courses.manage',
    'academic_years.read','academic_years.manage','semesters.read','semesters.manage'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Retain old grant history while removing obsolete capabilities from runtime.
UPDATE public.permissions SET is_active=false, updated_at=now()
WHERE code IN ('programs.read','programs.manage','subjects.read','subjects.manage',
              'sections.read','sections.manage','section_subjects.read','section_subjects.manage');

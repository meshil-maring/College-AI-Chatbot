-- Shared fixture for the member profile contracts. Included with \ir inside a
-- transaction that the contract rolls back; run only against a local database.
-- Institution A has an admin, Faculty F1/F2 and Staff S1; institution B has its
-- own admin and department so cross-tenant writes can be checked.
SET LOCAL request.jwt.claim.role = 'service_role';
SELECT set_config('request.jwt.claims', '{"role":"service_role"}', true);

CREATE SCHEMA member_fixture;
CREATE FUNCTION member_fixture.id(p_name text) RETURNS uuid LANGUAGE sql IMMUTABLE AS $$
    SELECT (CASE p_name
        WHEN 'org' THEN '0f000000-0000-4000-8000-000000000001'
        WHEN 'tenant' THEN '0f000000-0000-4000-8000-0000000000a1'
        WHEN 'tenant_b' THEN '0f000000-0000-4000-8000-0000000000b1'
        WHEN 'cse' THEN '0f000000-0000-4000-8000-0000000000c1'
        WHEN 'mech' THEN '0f000000-0000-4000-8000-0000000000c2'
        WHEN 'civil' THEN '0f000000-0000-4000-8000-0000000000c3'
        WHEN 'retired' THEN '0f000000-0000-4000-8000-0000000000c4'
        WHEN 'b_dept' THEN '0f000000-0000-4000-8000-0000000000c5'
        WHEN 'admin' THEN '0f000000-0000-4000-8000-00000000d001'
        WHEN 'admin_b' THEN '0f000000-0000-4000-8000-00000000d002'
        WHEN 'f1' THEN '0f000000-0000-4000-8000-00000000d003'
        WHEN 'f2' THEN '0f000000-0000-4000-8000-00000000d004'
        WHEN 's1' THEN '0f000000-0000-4000-8000-00000000d005'
        WHEN 'invitee' THEN '0f000000-0000-4000-8000-00000000d006'
    END)::uuid;
$$;

INSERT INTO public.organizations (organization_id, name, organization_code, official_email, contact_information, status)
VALUES (member_fixture.id('org'), 'Fixture Org', 'MEMBER-FIXTURE', 'org@member.test', '{}', 'active');
INSERT INTO public.institutions (institution_id, organization_id, name, code)
VALUES (member_fixture.id('tenant'), member_fixture.id('org'), 'Fixture College A', 'MFX-A'),
       (member_fixture.id('tenant_b'), member_fixture.id('org'), 'Fixture College B', 'MFX-B');
UPDATE public.institutions SET status = 'active', is_active = true
WHERE institution_id IN (member_fixture.id('tenant'), member_fixture.id('tenant_b'));

INSERT INTO public.departments (department_id, institution_id, name, code)
VALUES (member_fixture.id('cse'), member_fixture.id('tenant'), 'Computer Science', 'CSE'),
       (member_fixture.id('mech'), member_fixture.id('tenant'), 'Mechanical', 'ME'),
       (member_fixture.id('civil'), member_fixture.id('tenant'), 'Civil', 'CE'),
       (member_fixture.id('retired'), member_fixture.id('tenant'), 'Retired', 'RT'),
       (member_fixture.id('b_dept'), member_fixture.id('tenant_b'), 'Other College', 'OC');
UPDATE public.departments SET is_active = false WHERE department_id = member_fixture.id('retired');

INSERT INTO auth.users (id, email, instance_id, aud, role)
SELECT member_fixture.id(n), n || '@member.test', '00000000-0000-0000-0000-000000000000',
       'authenticated', 'authenticated'
FROM unnest(ARRAY['admin', 'admin_b', 'f1', 'f2', 's1', 'invitee']) n;
INSERT INTO public.users (id, auth_user_id, email, first_name, last_name)
SELECT member_fixture.id(n), member_fixture.id(n), n || '@member.test', initcap(n), 'Fixture'
FROM unnest(ARRAY['admin', 'admin_b', 'f1', 'f2', 's1', 'invitee']) n
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.user_roles (user_id, role_id, scope_type, scope_id, scope_organization_id)
SELECT member_fixture.id(v.who), r.id, 'institution', member_fixture.id(v.tenant), member_fixture.id('org')
FROM (VALUES ('admin', 'admin', 'tenant'), ('admin_b', 'admin', 'tenant_b'),
             ('f1', 'faculty', 'tenant'), ('f2', 'faculty', 'tenant'), ('s1', 'staff', 'tenant')) v(who, role, tenant)
JOIN public.roles r ON r.name = v.role;

INSERT INTO public.institution_member_departments (institution_id, user_id, department_id)
VALUES (member_fixture.id('tenant'), member_fixture.id('f1'), member_fixture.id('cse')),
       (member_fixture.id('tenant'), member_fixture.id('s1'), member_fixture.id('cse'));

-- A complete Faculty and Staff profile, varied by the employee ID.
CREATE FUNCTION member_fixture.faculty(p_employee_id text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
    SELECT jsonb_build_object(
        'common', jsonb_build_object('employee_id', p_employee_id, 'phone', '+91 98765 43210',
            'designation', 'Assistant Professor', 'joining_date', '2026-07-01'),
        'faculty', jsonb_build_object('qualification', 'M.Tech', 'specialization', 'Databases',
            'experience_years', 6.5, 'employment_type', 'permanent', 'employment_start_date', '2026-07-01'));
$$;
CREATE FUNCTION member_fixture.staff(p_employee_id text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
    SELECT jsonb_build_object(
        'common', jsonb_build_object('employee_id', p_employee_id,
            'designation', 'Office Assistant', 'joining_date', '2026-06-01'),
        'staff', jsonb_build_object('staff_category', 'office_administration',
            'employment_type', 'contractual', 'employment_start_date', '2026-06-01',
            'contract_end_date', '2027-05-31', 'responsibilities', jsonb_build_array('Admissions desk')));
$$;

-- Assert that a statement fails with the given SQLSTATE.
CREATE FUNCTION member_fixture.expect_error(p_sql text, p_state text, p_label text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_state text;
BEGIN
    BEGIN
        EXECUTE p_sql;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE;
        IF v_state <> p_state THEN
            RAISE EXCEPTION '%: expected SQLSTATE %, got % (%)', p_label, p_state, v_state, SQLERRM;
        END IF;
        RETURN;
    END;
    RAISE EXCEPTION '%: expected SQLSTATE %, but the statement succeeded', p_label, p_state;
END;
$$;

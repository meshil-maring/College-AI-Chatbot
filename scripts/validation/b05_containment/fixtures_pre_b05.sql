-- Synthetic-only owner fixture. NOT RUN. Requires psql variable fixture_anchor
-- taken once from the disposable database clock by a later authorized adapter.
-- Load after migration 39 for upgrade lane, or after 40 for empty-chain lane.
-- No trigger/constraint disabling; deliberately no B05 operation backfill.
BEGIN;
SET LOCAL search_path = public, extensions;
SET LOCAL timezone = 'UTC';
INSERT INTO public.organizations
  (organization_id,name,organization_code,official_email,contact_information,status)
VALUES
 ('10000000-0000-0000-0000-000000000001','Synthetic organization A','B05_ORG_A','org-a@example.invalid','Synthetic only','active'),
 ('10000000-0000-0000-0000-000000000002','Synthetic organization B','B05_ORG_B','org-b@example.invalid','Synthetic only','active');
INSERT INTO public.institutions(institution_id,name,code,organization_id,status)
VALUES
 ('20000000-0000-0000-0000-000000000001','Synthetic tenant A','B05_TENANT_A','10000000-0000-0000-0000-000000000001','active'),
 ('20000000-0000-0000-0000-000000000002','Synthetic tenant B','B05_TENANT_B','10000000-0000-0000-0000-000000000002','active'),
 ('20000000-0000-0000-0000-000000000003','Synthetic inactive tenant','B05_TENANT_OFF','10000000-0000-0000-0000-000000000001','suspended');
-- Empty baseline can lack application seed roles. These are fixture rows;
-- the ON CONFLICT preserves any role seeded by a historical migration.
INSERT INTO public.roles(id,name,description,is_active)
SELECT ('40000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid, name, 'Synthetic fixture role', true
FROM (VALUES (1,'super_admin'),(2,'admin'),(3,'staff'),(4,'faculty'),(5,'student')) r(n,name)
ON CONFLICT (name) DO NOTHING;
INSERT INTO auth.users(id,email,email_confirmed_at)
SELECT ('30000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
       label || '@example.invalid', CASE WHEN n=10 THEN NULL ELSE :'fixture_anchor'::timestamptz END
FROM (VALUES (1,'platform'),(2,'admin-a'),(3,'admin-b'),(4,'org-admin'),
 (5,'existing-a'),(6,'existing-b'),(7,'granted-staff'),(8,'inactive'),
 (9,'student'),(10,'unconfirmed'),(11,'faculty-recipient'),
 (12,'staff-recipient')) u(n,label);
INSERT INTO public.users(id,auth_user_id,email,first_name,last_name,status)
SELECT id,id,email,'Synthetic','Fixture',CASE WHEN email='inactive@example.invalid' THEN 'inactive' ELSE 'active' END
FROM auth.users WHERE id::text LIKE '30000000-%';
INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
SELECT ('30000000-0000-0000-0000-' || lpad(actor::text,12,'0'))::uuid,r.id,scope,
 CASE WHEN scope='platform' THEN NULL
      WHEN scope='organization' THEN '10000000-0000-0000-0000-000000000001'::uuid
      ELSE ('20000000-0000-0000-0000-' || lpad(tenant::text,12,'0'))::uuid END,
 CASE WHEN scope='platform' THEN NULL
      ELSE ('10000000-0000-0000-0000-' || lpad(tenant::text,12,'0'))::uuid END
FROM (VALUES (1,'super_admin','platform',0),(2,'admin','institution',1),
 (3,'admin','institution',2),(4,'admin','organization',1),
 (6,'staff','institution',2),(7,'staff','institution',1)) g(actor,name,scope,tenant)
JOIN public.roles r ON r.name=g.name;
INSERT INTO public.user_permission_grants
 (grant_id,user_id,institution_id,permission_id,granted_by,granted_at)
SELECT '41000000-0000-0000-0000-000000000001',
 '30000000-0000-0000-0000-000000000007','20000000-0000-0000-0000-000000000001',
 p.permission_id,'30000000-0000-0000-0000-000000000002',:'fixture_anchor'::timestamptz
FROM public.permissions p WHERE p.code='faculty.assignments.manage';
-- PENDING / previously APPROVED / REJECTED; rejected target already has a grant.
INSERT INTO public.institution_membership_requests
 (request_id,institution_id,organization_id,user_id,requested_role,official_email,
  status,decided_by_user_id,decided_at,decision_reason,created_at,updated_at)
SELECT ('50000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 '20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',
 u.id,role,u.email,state,
 CASE WHEN state='pending' THEN NULL ELSE '30000000-0000-0000-0000-000000000002'::uuid END,
 CASE WHEN state='pending' THEN NULL ELSE :'fixture_anchor'::timestamptz - interval '1 day' END,
 CASE WHEN state='pending' THEN NULL ELSE 'synthetic legacy decision' END,
 :'fixture_anchor'::timestamptz - interval '2 days',:'fixture_anchor'::timestamptz - interval '1 day'
FROM (VALUES (1,5,'staff','pending'),(2,11,'faculty','approved'),
 (3,7,'staff','rejected'),(4,6,'staff','pending'),(5,10,'staff','pending'),
 (6,12,'staff','approved')) m(n,person,role,state)
JOIN public.users u ON u.id=('30000000-0000-0000-0000-' || lpad(person::text,12,'0'))::uuid;
INSERT INTO public.students
 (student_id,user_id,institution_id,student_number,enrollment_date,email,approval_status)
VALUES ('51000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000009',
 '20000000-0000-0000-0000-000000000001','B05_SYNTHETIC_STUDENT',
 (:'fixture_anchor'::timestamptz AT TIME ZONE 'UTC')::date,'student@example.invalid','pending');
-- Institution invitations: valid existing/new, expired, cancelled, accepted
-- with incomplete historic linkage, and staff/faculty variants.
-- Pending uniqueness is (institution_id, lower(email)), not role_name.
-- Staff uses its own confirmed synthetic account and approved request, without
-- a grant, so the existing-account admin and staff scenarios remain independent.
INSERT INTO public.platform_admin_invitations
 (invitation_id,institution_id,email,token_hash,role_name,status,created_by,
  created_at,expires_at,accepted_at,accepted_user_id,cancelled_at)
SELECT ('60000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 '20000000-0000-0000-0000-000000000001',email || '@example.invalid',
 lpad(n::text,64,'0'),role,state,
 CASE WHEN role='admin' THEN '30000000-0000-0000-0000-000000000001'::uuid
      ELSE '30000000-0000-0000-0000-000000000002'::uuid END,
 :'fixture_anchor'::timestamptz - interval '2 days',
 :'fixture_anchor'::timestamptz + CASE WHEN state='expired' THEN interval '-1 day' ELSE interval '7 days' END,
 CASE WHEN state='accepted' THEN :'fixture_anchor'::timestamptz - interval '1 day' ELSE NULL END,
 NULL, CASE WHEN state='cancelled' THEN :'fixture_anchor'::timestamptz - interval '1 day' ELSE NULL END
FROM (VALUES (1,'existing-a','admin','invited'),(2,'new-account','admin','invited'),
 (3,'legacy-expired','admin','expired'),(4,'legacy-cancelled','admin','cancelled'),
 (5,'legacy-accepted','admin','accepted'),(6,'staff-recipient','staff','invited'),
 (7,'faculty-recipient','faculty','invited')) i(n,email,role,state);
INSERT INTO public.platform_super_admin_invitations
 (invitation_id,email,token_hash,status,created_by,created_at,expires_at,accepted_at)
SELECT ('61000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 label || '@example.invalid',lpad((100+n)::text,64,'0'),state,
 '30000000-0000-0000-0000-000000000001',:'fixture_anchor'::timestamptz - interval '2 days',
 :'fixture_anchor'::timestamptz + CASE WHEN state='expired' THEN interval '-1 day' ELSE interval '7 days' END,
 CASE WHEN state='accepted' THEN :'fixture_anchor'::timestamptz - interval '1 day' ELSE NULL END
FROM (VALUES (1,'platform-new','invited'),(2,'existing-a','invited'),
 (3,'platform-legacy-expired','expired'),(4,'platform-legacy-accepted','accepted')) i(n,label,state);
-- Outbox storage/trigger fixtures only. Deliberately invalid synthetic
-- ciphertext markers satisfy length shape; no worker may decrypt or send them.
INSERT INTO public.email_outbox
 (id,aggregate_id,protected_token,status,available_at,created_at,updated_at)
SELECT ('63000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 ('60000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 repeat('SYNTHETIC_NOT_CIPHERTEXT_',5),'pending',
 :'fixture_anchor'::timestamptz,:'fixture_anchor'::timestamptz,:'fixture_anchor'::timestamptz
FROM (VALUES (1),(2),(6),(7)) fixture(n);
-- Preserve known historical events without claiming current completion.
INSERT INTO public.admin_audit_log
 (audit_id,actor_user_id,institution_id,action,table_name,record_id,record_data,status,performed_at)
VALUES ('70000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000002',
 '20000000-0000-0000-0000-000000000001','synthetic.history','institution_membership_requests',
 '50000000-0000-0000-0000-000000000002','{"synthetic":true,"historic_only":true}',
 'info',:'fixture_anchor'::timestamptz - interval '1 day');
INSERT INTO public.auth_security_events(event_id,user_id,auth_user_id,event,status,occurred_at)
VALUES ('71000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005',
 '30000000-0000-0000-0000-000000000005','synthetic.historic_verification','info',
 :'fixture_anchor'::timestamptz - interval '1 day');
COMMIT;

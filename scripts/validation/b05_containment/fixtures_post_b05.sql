-- Synthetic interruption snapshots only. NOT RUN. Requires fixture_anchor.
-- Load after migration 40. Owner inserts do not prove RPC reachability.
BEGIN;
SET LOCAL timezone = 'UTC';
CREATE TEMP TABLE b05_snapshot_specs(n integer,stage text) ON COMMIT DROP;
INSERT INTO b05_snapshot_specs VALUES
 (21,'reserved'),(22,'provider_started'),(23,'provider_created'),
 (24,'user_created'),(25,'accepted'),(26,'confirmed');
INSERT INTO auth.users(id,email,email_confirmed_at)
SELECT ('32000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 stage || '@example.invalid',CASE WHEN stage='confirmed' THEN :'fixture_anchor'::timestamptz ELSE NULL END
FROM b05_snapshot_specs WHERE n>=23;
INSERT INTO public.users(id,auth_user_id,email,first_name,last_name)
SELECT ('33000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 ('32000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 stage || '@example.invalid','Synthetic','Snapshot'
FROM b05_snapshot_specs WHERE n>=24;
INSERT INTO public.platform_admin_invitations
 (invitation_id,institution_id,email,token_hash,role_name,status,created_by,
  created_at,expires_at,acceptance_id,accepted_at,accepted_user_id)
SELECT ('62000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 '20000000-0000-0000-0000-000000000001',stage || '@example.invalid',lpad((200+n)::text,64,'0'),
 'admin',CASE WHEN n>=25 THEN 'accepted' ELSE 'invited' END,
 '30000000-0000-0000-0000-000000000001',:'fixture_anchor'::timestamptz - interval '1 day',
 :'fixture_anchor'::timestamptz + interval '7 days',
 ('80000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,
 CASE WHEN n>=25 THEN :'fixture_anchor'::timestamptz ELSE NULL END,
 CASE WHEN n>=25 THEN ('33000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid ELSE NULL END
FROM b05_snapshot_specs;
INSERT INTO public.b05_invitation_operations
 (acceptance_id,kind,invitation_id,stage,auth_user_id,user_id,new_account,updated_at)
SELECT ('80000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,'institution',
 ('62000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,stage,
 CASE WHEN n>=23 THEN ('32000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid ELSE NULL END,
 CASE WHEN n>=24 THEN ('33000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid ELSE NULL END,
 true,:'fixture_anchor'::timestamptz
FROM b05_snapshot_specs;
INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
SELECT ('33000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid,r.id,'institution',
 '20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001'
FROM b05_snapshot_specs CROSS JOIN public.roles r WHERE n>=25 AND r.name='admin';
INSERT INTO public.admin_audit_log
 (audit_id,actor_user_id,institution_id,action,table_name,record_id,record_data,status,decision_key,performed_at)
VALUES ('70000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000002',
 '20000000-0000-0000-0000-000000000001','membership.rejected','institution_membership_requests',
 '50000000-0000-0000-0000-000000000003','{"synthetic":true,"status":"rejected"}',
 'success','membership:50000000-0000-0000-0000-000000000003',:'fixture_anchor'::timestamptz);
-- An existing repair event and an independent missing-event legacy fixture.
INSERT INTO public.b05_invitation_lifecycle_audit
 (kind,invitation_id,status,actor_user_id,attribution,repaired,performed_at)
VALUES ('institution','60000000-0000-0000-0000-000000000004','cancelled',NULL,
 'unrecorded_initiator',true,:'fixture_anchor'::timestamptz);
COMMIT;

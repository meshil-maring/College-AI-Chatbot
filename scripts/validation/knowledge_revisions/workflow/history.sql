BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
CREATE TABLE knowledge_fixture.policies(name text PRIMARY KEY, policy jsonb NOT NULL);
INSERT INTO knowledge_fixture.policies VALUES('student', public.snapshot_knowledge_policy(
    knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), ARRAY[knowledge_fixture.id('wf_students_chunk')]));
SELECT knowledge_fixture.assert_true('Allowed history provenance validates',
    public.check_knowledge_policy(knowledge_fixture.id('wf_student'), (SELECT policy FROM knowledge_fixture.policies WHERE name = 'student')));
SELECT knowledge_fixture.assert_true('Same provenance is denied to a different audience',
    NOT public.check_knowledge_policy(knowledge_fixture.id('wf_staff'), (SELECT policy FROM knowledge_fixture.policies WHERE name = 'student')));
SELECT knowledge_fixture.reject('Forbidden chunks cannot enter a generated turn snapshot', $q$
    SELECT public.snapshot_knowledge_policy(knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'),
        ARRAY[knowledge_fixture.id('wf_staff_only_chunk')])
$q$, ARRAY['40001']);
SELECT knowledge_fixture.workflow_decide('wf_students', 'unpublish');
SELECT knowledge_fixture.assert_true('Unpublication revokes stored history provenance',
    NOT public.check_knowledge_policy(knowledge_fixture.id('wf_student'), (SELECT policy FROM knowledge_fixture.policies WHERE name = 'student')));
SELECT knowledge_fixture.reject('Unpublished sources cannot re-enter follow-up context', $q$
    SELECT public.snapshot_knowledge_policy(knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), '{}',
        (SELECT policy FROM knowledge_fixture.policies WHERE name = 'student'))
$q$, ARRAY['40001']);
SELECT knowledge_fixture.assert_true('Legacy unverified history is not treated as authorized',
    NOT public.check_knowledge_policy(knowledge_fixture.id('wf_student'), NULL));
SELECT knowledge_fixture.assert_true('Malformed provenance is denied',
    NOT public.check_knowledge_policy(knowledge_fixture.id('wf_student'), '{"institution_id":"invalid","sources":{},"versions":{}}'));
INSERT INTO knowledge_fixture.policies VALUES('public', public.snapshot_public_knowledge_policy(' tenant-knowledge-test '));
SELECT knowledge_fixture.assert_true('Public snapshot resolves a normalized public institution code',
    (SELECT policy->>'institution_id' = knowledge_fixture.id('tenant')::text FROM knowledge_fixture.policies WHERE name = 'public'));

INSERT INTO knowledge_fixture.policies VALUES('members', public.snapshot_knowledge_policy(
    knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), ARRAY[knowledge_fixture.id('wf_members_chunk')]));
DO $$
DECLARE revision jsonb;
BEGIN
    revision := public.save_knowledge_draft(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        '{"visibility":"restricted","audience_roles":["staff"]}', knowledge_fixture.id('wf_members'));
    INSERT INTO knowledge_fixture.ids VALUES('wf_replacement', knowledge_fixture.id('wf_members')),
        ('wf_replacement_revision', (revision->>'revision_id')::uuid);
END;
$$;
SELECT knowledge_fixture.assert_true('A proposed audience change leaves current access intact',
    public.knowledge_source_allowed(knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), knowledge_fixture.id('wf_members')));
SELECT knowledge_fixture.workflow_decide('wf_replacement', 'submit');
SELECT knowledge_fixture.workflow_decide('wf_replacement', 'approve');
SELECT knowledge_fixture.reject('Publication rejects a stale live policy token', $q$
    SELECT public.decide_knowledge_revision(knowledge_fixture.id('tenant_actor'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('wf_replacement_revision'), 'publish',
        (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('wf_replacement_revision')),
        (SELECT policy_version - 1 FROM public.knowledge_sources WHERE knowledge_source_id = knowledge_fixture.id('wf_members')))
$q$, ARRAY['40001']);
SELECT knowledge_fixture.workflow_decide('wf_replacement', 'publish');
SELECT knowledge_fixture.assert_true('Publishing a narrowed audience revokes the old reader and history',
    NOT public.knowledge_source_allowed(knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), knowledge_fixture.id('wf_members'))
    AND NOT public.check_knowledge_policy(knowledge_fixture.id('wf_student'), (SELECT policy FROM knowledge_fixture.policies WHERE name = 'members'))
    AND public.knowledge_source_allowed(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('wf_members')));
SELECT knowledge_fixture.assert_true('Audience-only publication reuses the reviewed indexed version',
    public.knowledge_version_allowed(knowledge_fixture.id('wf_members'), knowledge_fixture.id('wf_members_version'))
    AND (SELECT lifecycle_status = 'superseded' FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('wf_members_revision')));
SELECT knowledge_fixture.workflow_decide('wf_public', 'unpublish');
SELECT knowledge_fixture.assert_true('Unpublication invalidates the public corpus snapshot',
    public.snapshot_public_knowledge_policy('TENANT-KNOWLEDGE-TEST') <>
        (SELECT policy FROM knowledge_fixture.policies WHERE name = 'public'));
COMMIT;

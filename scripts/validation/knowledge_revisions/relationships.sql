BEGIN;
SELECT knowledge_fixture.resource('candidate', 'restricted', 'draft');
SELECT knowledge_fixture.revision('candidate_rev', 'candidate');
SELECT knowledge_fixture.assert_true('New revision defaults to private draft',
    (SELECT lifecycle_status = 'draft' AND visibility = 'restricted' AND revision_version = 1
     FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('candidate_rev'))
    AND (SELECT published_revision_id IS NULL FROM public.knowledge_sources
         WHERE knowledge_source_id = knowledge_fixture.id('candidate')));

SELECT knowledge_fixture.reject('Cross-institution revision rejected', $q$
    INSERT INTO public.knowledge_source_revisions (
        knowledge_source_id, institution_id, revision_number, title, source_type, created_by_user_id
    ) VALUES (knowledge_fixture.id('candidate'), knowledge_fixture.id('foreign_tenant'),
              99, 'Cross tenant', 'handbook', knowledge_fixture.id('tenant_actor'))
$q$, ARRAY['23503']);
SELECT knowledge_fixture.reject('Unknown audience role rejected', $q$
    INSERT INTO public.knowledge_source_revision_audiences VALUES (knowledge_fixture.id('candidate_rev'), 'teacher')
$q$, ARRAY['23514']);

INSERT INTO public.knowledge_source_revision_audiences VALUES
    (knowledge_fixture.id('candidate_rev'), 'student'), (knowledge_fixture.id('candidate_rev'), 'faculty');
SELECT knowledge_fixture.attach('candidate_rev', 'candidate');
SELECT knowledge_fixture.assert_true('Multiple explicit roles share one revision',
    (SELECT count(*) = 2 FROM public.knowledge_source_revision_audiences
        WHERE revision_id = knowledge_fixture.id('candidate_rev')));
SELECT knowledge_fixture.assert_true('Audience and manifest edits advance concurrency token',
    (SELECT revision_version > 1 FROM public.knowledge_source_revisions
        WHERE revision_id = knowledge_fixture.id('candidate_rev')));

SELECT knowledge_fixture.reject('Duplicate role rejected', $q$
    INSERT INTO public.knowledge_source_revision_audiences VALUES (knowledge_fixture.id('candidate_rev'), 'student')
$q$, ARRAY['23505']);
SELECT knowledge_fixture.reject('Document from another source rejected', $q$
    INSERT INTO public.knowledge_source_revision_documents VALUES (
        knowledge_fixture.id('candidate_rev'), knowledge_fixture.id('candidate'),
        knowledge_fixture.id('foreign_document'), knowledge_fixture.id('foreign_version'))
$q$, ARRAY['23503']);
SELECT knowledge_fixture.reject('Version from another document rejected', $q$
    UPDATE public.knowledge_source_revision_documents SET document_version_id = knowledge_fixture.id('foreign_version')
        WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23503']);
SELECT knowledge_fixture.reject('Cross-source live pointer rejected', $q$
    UPDATE public.knowledge_sources SET published_revision_id = (
        SELECT published_revision_id FROM public.knowledge_sources WHERE knowledge_source_id = knowledge_fixture.id('foreign'))
    WHERE knowledge_source_id = knowledge_fixture.id('candidate')
$q$, ARRAY['23503', '23514']);
SELECT knowledge_fixture.reject('Duplicate source revision number rejected', $q$
    INSERT INTO public.knowledge_source_revisions (
        knowledge_source_id, institution_id, revision_number, title, source_type, created_by_user_id
    ) VALUES (knowledge_fixture.id('candidate'), knowledge_fixture.id('tenant'),
              1, 'Duplicate', 'handbook', knowledge_fixture.id('tenant_actor'))
$q$, ARRAY['23505']);

SELECT knowledge_fixture.revision('public_draft', 'candidate', 'public');
SELECT knowledge_fixture.reject('Public audience cannot also target a role', $q$
    INSERT INTO public.knowledge_source_revision_audiences VALUES (knowledge_fixture.id('public_draft'), 'student')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.revision('empty_audience', 'candidate');
SELECT knowledge_fixture.attach('empty_audience', 'candidate');
SELECT knowledge_fixture.reject('Empty selected audience cannot be submitted', $q$
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'under_review', submitted_at = now()
        WHERE revision_id = knowledge_fixture.id('empty_audience')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.revision('empty_manifest', 'candidate');
INSERT INTO public.knowledge_source_revision_audiences VALUES (knowledge_fixture.id('empty_manifest'), 'staff');
SELECT knowledge_fixture.reject('Empty file manifest cannot be submitted', $q$
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'under_review', submitted_at = now()
        WHERE revision_id = knowledge_fixture.id('empty_manifest')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Invalid effective dates rejected', $q$
    UPDATE public.knowledge_source_revisions SET effective_from = CURRENT_DATE, effective_until = CURRENT_DATE - 1
        WHERE revision_id = knowledge_fixture.id('empty_manifest')
$q$, ARRAY['23514']);

SELECT knowledge_fixture.resource('editable_file', 'restricted', 'draft');
SELECT knowledge_fixture.revision('editable_revision', 'editable_file');
SELECT knowledge_fixture.attach('editable_revision', 'editable_file');
CREATE TABLE knowledge_fixture.file_tokens AS SELECT revision_version AS expected
    FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('editable_revision');
UPDATE public.document_versions SET original_filename = 'corrected-draft-name.pdf'
    WHERE document_version_id = knowledge_fixture.id('editable_file_version');
SELECT knowledge_fixture.assert_true('Draft file edits advance the parent review token',
    (SELECT revision_version > (SELECT expected FROM knowledge_fixture.file_tokens)
     FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('editable_revision')));
COMMIT;

BEGIN;
SELECT knowledge_fixture.reject('Draft cannot skip review', $q$
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'approved'
        WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
UPDATE public.knowledge_source_revisions SET lifecycle_status = 'under_review', submitted_at = now()
    WHERE revision_id = knowledge_fixture.id('candidate_rev');
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
SELECT knowledge_fixture.reject('Submitted audience cannot change', $q$
    DELETE FROM public.knowledge_source_revision_audiences WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Submitted metadata cannot change', $q$
    UPDATE public.knowledge_source_revisions SET title = 'Changed after review started'
        WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Approval requires reviewer provenance', $q$
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'approved'
        WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
UPDATE public.knowledge_source_revisions SET lifecycle_status = 'draft', review_notes = 'Please revise.'
    WHERE revision_id = knowledge_fixture.id('candidate_rev');
SELECT knowledge_fixture.approve('candidate_rev');
UPDATE public.knowledge_source_revisions SET lifecycle_status = 'draft'
    WHERE revision_id = knowledge_fixture.id('candidate_rev');
SELECT knowledge_fixture.assert_true('Returning to draft clears approval',
    (SELECT approved_by_user_id IS NULL AND reviewed_by_user_id IS NULL
        AND approved_at IS NULL AND submitted_at IS NULL
     FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('candidate_rev')));
SELECT knowledge_fixture.approve('candidate_rev');
SELECT knowledge_fixture.publish('candidate_rev');
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
SELECT knowledge_fixture.assert_true('Owner transaction publishes exact revision and policy',
    (SELECT published_revision_id = knowledge_fixture.id('candidate_rev')
        AND visibility = 'restricted' AND policy_version = 1
     FROM public.knowledge_sources WHERE knowledge_source_id = knowledge_fixture.id('candidate')));
SELECT knowledge_fixture.reject('Published metadata immutable', $q$
    UPDATE public.knowledge_source_revisions SET title = 'Tampered'
        WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Published audience immutable', $q$
    DELETE FROM public.knowledge_source_revision_audiences WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Published manifest immutable', $q$
    DELETE FROM public.knowledge_source_revision_documents WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Published history cannot be deleted', $q$
    DELETE FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Reviewed file cannot be rewritten', $q$
    UPDATE public.document_versions SET storage_object_key = 'changed'
        WHERE document_version_id = knowledge_fixture.id('candidate_version')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Live file cannot be superseded early', $q$
    UPDATE public.document_versions SET lifecycle_status = 'superseded'
        WHERE document_version_id = knowledge_fixture.id('candidate_version')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Live file cannot lose its successful processing run', $q$
    DELETE FROM public.document_processing_runs
        WHERE document_version_id = knowledge_fixture.id('candidate_version')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Live processing cannot become unindexed', $q$
    UPDATE public.document_processing_runs SET embedding_status = 'failed'
        WHERE document_version_id = knowledge_fixture.id('candidate_version')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Live source metadata cannot diverge', $q$
    UPDATE public.knowledge_sources SET title = 'Changed outside revision'
        WHERE knowledge_source_id = knowledge_fixture.id('candidate')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Live pointer cannot be cleared alone', $q$
    UPDATE public.knowledge_sources SET published_revision_id = NULL
        WHERE knowledge_source_id = knowledge_fixture.id('candidate')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Live revision cannot be archived alone', $q$
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'archived'
        WHERE revision_id = knowledge_fixture.id('candidate_rev')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Policy version cannot be assigned by caller', $q$
    UPDATE public.knowledge_sources SET policy_version = 900
        WHERE knowledge_source_id = knowledge_fixture.id('candidate')
$q$, ARRAY['23514']);

SELECT knowledge_fixture.revision('replacement', 'candidate', 'authenticated');
SELECT knowledge_fixture.attach('replacement', 'candidate');
SELECT knowledge_fixture.assert_true('Replacement draft leaves live revision unchanged',
    (SELECT published_revision_id = knowledge_fixture.id('candidate_rev') AND policy_version = 1
     FROM public.knowledge_sources WHERE knowledge_source_id = knowledge_fixture.id('candidate')));
SELECT knowledge_fixture.approve('replacement');
SELECT knowledge_fixture.publish('replacement');
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
SELECT knowledge_fixture.assert_true('Atomic replacement advances live audience and policy version',
    (SELECT published_revision_id = knowledge_fixture.id('replacement')
        AND visibility = 'authenticated' AND policy_version = 2
     FROM public.knowledge_sources WHERE knowledge_source_id = knowledge_fixture.id('candidate'))
    AND (SELECT lifecycle_status = 'superseded' FROM public.knowledge_source_revisions
         WHERE revision_id = knowledge_fixture.id('candidate_rev')));

SELECT knowledge_fixture.revision('not_indexed', 'failed');
INSERT INTO public.knowledge_source_revision_audiences VALUES (knowledge_fixture.id('not_indexed'), 'staff');
SELECT knowledge_fixture.attach('not_indexed', 'failed');
SELECT knowledge_fixture.approve('not_indexed');
SELECT knowledge_fixture.reject('Failed indexing prevents publication', $q$
    SELECT knowledge_fixture.publish('not_indexed')
$q$, ARRAY['23514']);

SELECT knowledge_fixture.revision('race_rev', 'candidate');
INSERT INTO public.knowledge_source_revision_audiences VALUES (knowledge_fixture.id('race_rev'), 'student');
SELECT knowledge_fixture.attach('race_rev', 'candidate');
CREATE TABLE knowledge_fixture.review_tokens AS SELECT revision_version AS expected
    FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('race_rev');
COMMIT;

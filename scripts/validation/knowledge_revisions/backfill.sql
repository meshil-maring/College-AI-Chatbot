BEGIN;
SELECT knowledge_fixture.assert_true('Legacy source metadata is unchanged',
    (SELECT count(*) FROM public.knowledge_sources) = (SELECT count(*) FROM knowledge_fixture.original_sources)
    AND NOT EXISTS (SELECT 1 FROM knowledge_fixture.original_sources original
        JOIN public.knowledge_sources source USING (knowledge_source_id)
        WHERE original.data IS DISTINCT FROM to_jsonb(source) - ARRAY['published_revision_id', 'policy_version']));
SELECT knowledge_fixture.assert_true('Legacy document versions are unchanged',
    (SELECT count(*) FROM public.document_versions) = (SELECT count(*) FROM knowledge_fixture.original_versions)
    AND NOT EXISTS (SELECT 1 FROM knowledge_fixture.original_versions original
        JOIN public.document_versions version USING (document_version_id)
        WHERE original.data IS DISTINCT FROM to_jsonb(version)));
SELECT knowledge_fixture.assert_true('Only three eligible sources receive snapshots',
    (SELECT count(*) = 3 FROM public.knowledge_source_revisions)
    AND (SELECT count(*) = 3 FROM public.knowledge_sources WHERE published_revision_id IS NOT NULL));
SELECT knowledge_fixture.assert_true('No targets or historical approval are invented',
    (SELECT count(*) = 0 FROM public.knowledge_source_revision_audiences)
    AND NOT EXISTS (SELECT 1 FROM public.knowledge_source_revisions WHERE NOT is_legacy_snapshot
                    OR approved_by_user_id IS NOT NULL OR reviewed_by_user_id IS NOT NULL));
SELECT knowledge_fixture.assert_true('Newest eligible version selected deterministically',
    (SELECT manifest.document_version_id = knowledge_fixture.id('public_latest')
     FROM public.knowledge_source_revision_documents manifest
     WHERE manifest.knowledge_source_id = knowledge_fixture.id('public')));
SELECT knowledge_fixture.assert_true('Ineligible legacy sources remain without a revision pointer',
    NOT EXISTS (SELECT 1 FROM public.knowledge_sources WHERE title NOT IN ('public', 'institution', 'foreign')
                AND (published_revision_id IS NOT NULL OR policy_version <> 0)));
SELECT knowledge_fixture.assert_true('Backfill preserves institution isolation',
    NOT EXISTS (SELECT 1 FROM public.knowledge_source_revisions revision
                JOIN public.knowledge_sources source USING (knowledge_source_id)
                WHERE revision.institution_id <> source.institution_id));
COMMIT;

CREATE FUNCTION knowledge_fixture.assert_true(label text, condition boolean) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF condition IS DISTINCT FROM true THEN RAISE EXCEPTION 'FAILED: %', label; END IF;
    INSERT INTO knowledge_fixture.results VALUES (label, true);
END;
$$;

CREATE FUNCTION knowledge_fixture.reject(label text, statement text, expected text[])
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE statement;
        SET CONSTRAINTS ALL IMMEDIATE;
        RAISE EXCEPTION 'Expected rejection: %', label;
    EXCEPTION WHEN OTHERS THEN
        IF NOT SQLSTATE = ANY(expected) THEN RAISE; END IF;
    END;
    SET CONSTRAINTS ALL DEFERRED;
    PERFORM knowledge_fixture.assert_true(label, true);
END;
$$;

CREATE FUNCTION knowledge_fixture.revision(key text, source_key text, audience text DEFAULT 'restricted')
RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE result uuid;
BEGIN
    INSERT INTO public.knowledge_source_revisions (
        knowledge_source_id, institution_id, revision_number, title, description,
        source_type, authority_level, visibility, effective_from, effective_until, created_by_user_id
    ) SELECT source.knowledge_source_id, source.institution_id,
        COALESCE((SELECT max(revision_number) + 1 FROM public.knowledge_source_revisions r
                  WHERE r.knowledge_source_id = source.knowledge_source_id), 1),
        source.title, source.description, source.source_type, source.authority_level,
        audience, source.effective_from, source.effective_until, source.created_by_user_id
      FROM public.knowledge_sources source WHERE source.knowledge_source_id = knowledge_fixture.id(source_key)
      RETURNING revision_id INTO result;
    INSERT INTO knowledge_fixture.ids VALUES (key, result);
    RETURN result;
END;
$$;

CREATE FUNCTION knowledge_fixture.attach(revision_key text, resource_key text)
RETURNS void LANGUAGE sql AS $$
    INSERT INTO public.knowledge_source_revision_documents (
        revision_id, knowledge_source_id, document_id, document_version_id
    ) VALUES (knowledge_fixture.id(revision_key), knowledge_fixture.id(resource_key),
              knowledge_fixture.id(resource_key || '_document'), knowledge_fixture.id(resource_key || '_version'));
$$;

-- Owner-only fixture helpers simulate transactions; none are deployed.
CREATE FUNCTION knowledge_fixture.approve(revision_key text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'under_review', submitted_at = now()
        WHERE revision_id = knowledge_fixture.id(revision_key);
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'approved',
        reviewed_by_user_id = knowledge_fixture.id('tenant_actor'), reviewed_at = now(),
        approved_by_user_id = knowledge_fixture.id('tenant_actor'), approved_at = now()
        WHERE revision_id = knowledge_fixture.id(revision_key);
END;
$$;

CREATE FUNCTION knowledge_fixture.publish(revision_key text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE candidate public.knowledge_source_revisions;
BEGIN
    SELECT * INTO STRICT candidate FROM public.knowledge_source_revisions
        WHERE revision_id = knowledge_fixture.id(revision_key);
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'superseded'
        WHERE knowledge_source_id = candidate.knowledge_source_id AND lifecycle_status = 'published';
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'published', published_at = now()
        WHERE revision_id = candidate.revision_id;
    UPDATE public.knowledge_sources SET published_revision_id = candidate.revision_id,
        title = candidate.title, description = candidate.description, source_type = candidate.source_type,
        authority_level = candidate.authority_level, visibility = candidate.visibility,
        lifecycle_status = 'published', effective_from = candidate.effective_from,
        effective_until = candidate.effective_until
        WHERE knowledge_source_id = candidate.knowledge_source_id;
END;
$$;

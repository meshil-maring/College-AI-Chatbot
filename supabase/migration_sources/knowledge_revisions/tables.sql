-- Additive foundation. No browser writes or publication RPC is enabled here.
ALTER TABLE public.knowledge_sources
    ADD COLUMN published_revision_id uuid,
    ADD COLUMN policy_version bigint NOT NULL DEFAULT 0
        CHECK (policy_version >= 0),
    ADD CONSTRAINT knowledge_sources_id_institution_key
        UNIQUE (knowledge_source_id, institution_id);

ALTER TABLE public.documents
    ADD CONSTRAINT documents_id_source_key UNIQUE (document_id, knowledge_source_id);
ALTER TABLE public.document_versions
    ADD CONSTRAINT document_versions_id_document_key UNIQUE (document_version_id, document_id);

CREATE TABLE public.knowledge_source_revisions (
    revision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_source_id uuid NOT NULL,
    institution_id uuid NOT NULL,
    revision_number integer NOT NULL CHECK (revision_number > 0),
    revision_version bigint NOT NULL DEFAULT 1 CHECK (revision_version > 0),
    title text NOT NULL CHECK (btrim(title) <> ''),
    description text,
    source_type text NOT NULL CHECK (btrim(source_type) <> ''),
    authority_level text NOT NULL DEFAULT 'standard' CHECK (btrim(authority_level) <> ''),
    visibility text NOT NULL DEFAULT 'restricted'
        CHECK (visibility IN ('public', 'authenticated', 'restricted')),
    lifecycle_status text NOT NULL DEFAULT 'draft'
        CHECK (lifecycle_status IN ('draft', 'under_review', 'approved',
                                    'published', 'archived', 'superseded')),
    effective_from date,
    effective_until date,
    created_by_user_id uuid NOT NULL REFERENCES public.users(id),
    reviewed_by_user_id uuid REFERENCES public.users(id),
    approved_by_user_id uuid REFERENCES public.users(id),
    review_notes text,
    submitted_at timestamptz,
    reviewed_at timestamptz,
    approved_at timestamptz,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    is_legacy_snapshot boolean NOT NULL DEFAULT false,
    CONSTRAINT knowledge_revision_dates CHECK (
        effective_until IS NULL OR effective_from IS NULL OR effective_until >= effective_from),
    CONSTRAINT knowledge_revision_source_tenant FOREIGN KEY (knowledge_source_id, institution_id)
        REFERENCES public.knowledge_sources(knowledge_source_id, institution_id),
    CONSTRAINT knowledge_revision_number UNIQUE (knowledge_source_id, revision_number),
    CONSTRAINT knowledge_revision_source_key UNIQUE (revision_id, knowledge_source_id),
    CONSTRAINT knowledge_revision_tenant_key
        UNIQUE (revision_id, knowledge_source_id, institution_id),
    CONSTRAINT knowledge_revision_review_provenance CHECK (
        is_legacy_snapshot OR lifecycle_status NOT IN ('approved', 'published')
        OR (reviewed_by_user_id IS NOT NULL AND approved_by_user_id IS NOT NULL
            AND reviewed_at IS NOT NULL AND approved_at IS NOT NULL)),
    CONSTRAINT knowledge_revision_submission_time CHECK (
        is_legacy_snapshot OR lifecycle_status NOT IN ('under_review', 'approved', 'published')
        OR submitted_at IS NOT NULL),
    CONSTRAINT knowledge_revision_review_time_order CHECK (
        is_legacy_snapshot OR (
            (reviewed_at IS NULL OR submitted_at IS NULL OR reviewed_at >= submitted_at)
            AND (approved_at IS NULL OR reviewed_at IS NULL OR approved_at >= reviewed_at)
            AND (published_at IS NULL OR approved_at IS NULL OR published_at >= approved_at))),
    CONSTRAINT knowledge_revision_publication_time CHECK (
        lifecycle_status <> 'published' OR published_at IS NOT NULL)
);

CREATE TABLE public.knowledge_source_revision_audiences (
    revision_id uuid NOT NULL REFERENCES public.knowledge_source_revisions(revision_id)
        ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('student', 'staff', 'faculty', 'admin')),
    PRIMARY KEY (revision_id, role)
);

CREATE TABLE public.knowledge_source_revision_documents (
    revision_id uuid NOT NULL,
    knowledge_source_id uuid NOT NULL,
    document_id uuid NOT NULL,
    document_version_id uuid NOT NULL,
    PRIMARY KEY (revision_id, document_id),
    CONSTRAINT knowledge_manifest_revision_source FOREIGN KEY (revision_id, knowledge_source_id)
        REFERENCES public.knowledge_source_revisions(revision_id, knowledge_source_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_manifest_document_source FOREIGN KEY (document_id, knowledge_source_id)
        REFERENCES public.documents(document_id, knowledge_source_id),
    CONSTRAINT knowledge_manifest_version_document FOREIGN KEY (document_version_id, document_id)
        REFERENCES public.document_versions(document_version_id, document_id)
);

ALTER TABLE public.knowledge_sources
    ADD CONSTRAINT knowledge_source_published_revision FOREIGN KEY (
        published_revision_id, knowledge_source_id, institution_id)
        REFERENCES public.knowledge_source_revisions(revision_id, knowledge_source_id, institution_id)
        DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX knowledge_revision_tenant_review_idx
    ON public.knowledge_source_revisions(institution_id, lifecycle_status, created_at DESC);
CREATE INDEX knowledge_revision_creator_idx
    ON public.knowledge_source_revisions(created_by_user_id, institution_id, created_at DESC);
CREATE INDEX knowledge_revision_role_idx
    ON public.knowledge_source_revision_audiences(role, revision_id);
CREATE INDEX knowledge_manifest_version_idx
    ON public.knowledge_source_revision_documents(document_version_id);
CREATE INDEX knowledge_manifest_source_idx
    ON public.knowledge_source_revision_documents(knowledge_source_id, document_id);
CREATE UNIQUE INDEX knowledge_revision_one_live_idx
    ON public.knowledge_source_revisions(knowledge_source_id) WHERE lifecycle_status = 'published';

COMMENT ON COLUMN public.knowledge_sources.published_revision_id IS
    'Reviewed revision and exact file manifest; null means no revision-managed publication.';
COMMENT ON COLUMN public.knowledge_source_revisions.is_legacy_snapshot IS
    'Migration provenance only; never fabricates historical administrator approval.';

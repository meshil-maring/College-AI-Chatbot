/**
 * Phase Admin-4 / Phase 6.19 — Document manager.
 *
 * Upload documents to knowledge sources and manage existing documents.
 * Shows processing status: upload → extraction → chunking → embedding → ready/error.
 *
 * Phase 6.19 hardening: the tenant is no longer a hardcoded demo institution
 * constant. It is derived exclusively from the server-authoritative identity
 * held in AuthProvider state (`/auth/me` -> `user.institution_id`);
 * `?institution_id=` remains only a server-validated filter, never an
 * authorization input. When the account has no institution linked
 * (platform-level), a controlled neutral state is shown and knowledge-source
 * creation is disabled instead of silently targeting a guessed tenant.
 */

import { useDocumentManager } from './useDocumentManager.ts'

export default function DocumentManager() {
  const model = useDocumentManager()
  const {
    institutionId,
    knowledgeSources,
    isSourcesLoading,
    sourcesError,
    documents,
    isLoading,
    error,
    knowledgeSourceId,
    setKnowledgeSourceId,
    uploading,
    uploadStatus,
    loadSources,
    handleUpload,
    handleNewVersion,
    handleCreateKnowledgeSource,
    handleDelete,
  } = model

  return (
    <div className="space-y-4">
      <h2 className="font-bold text-content text-section">Documents</h2>
      {error !== null && (
        <div role="alert" className="rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}
      <div className="rounded-lg border border-line bg-surface p-4 space-y-3">
        <label className="block">
          <span className="text-xs text-muted">Knowledge Source</span>
          {institutionId === null ? (
            <p role="status" className="mt-1 text-sm text-muted">
              No institution is linked to your administrator account, so there are no knowledge sources to manage yet.
            </p>
          ) : isSourcesLoading ? (
            <p className="mt-1 text-sm text-muted">Loading knowledge sources…</p>
          ) : sourcesError !== null ? (
            <div className="mt-1 space-y-2">
              <p role="alert" className="text-sm text-danger">
                {sourcesError}
              </p>
              <button
                type="button"
                onClick={() => void loadSources()}
                className="rounded-lg border border-control bg-surface px-3 py-2 text-xs font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
              >
                Retry
              </button>
            </div>
          ) : knowledgeSources.length === 0 ? (
            <div className="mt-1 space-y-2">
              <p className="text-sm text-muted">No knowledge sources yet. Create one to upload documents.</p>
              <button
                type="button"
                onClick={() => void handleCreateKnowledgeSource()}
                className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
              >
                New Knowledge Source
              </button>
            </div>
          ) : (
            <div className="mt-1 flex gap-2">
              <select
                value={knowledgeSourceId}
                onChange={(e) => setKnowledgeSourceId(e.target.value)}
                className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                {knowledgeSources.map((ks) => (
                  <option key={ks.knowledge_source_id} value={ks.knowledge_source_id}>
                    {ks.title} ({ks.knowledge_source_id.slice(0, 8)}…)
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void handleCreateKnowledgeSource()}
                title="New knowledge source"
                className="shrink-0 rounded-lg border border-control bg-surface px-3 py-2 text-sm font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
              >
                +
              </button>
            </div>
          )}
        </label>
        <div>
          <label className="block">
            <span className="text-xs text-muted">Upload Document</span>
            <input
              type="file"
              onChange={handleUpload}
              disabled={uploading || knowledgeSourceId.trim().length === 0}
              className="mt-1 block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-accent file:px-3 file:py-2 file:text-sm file:font-medium file:text-ink hover:file:bg-accent-hover disabled:file:opacity-50"
            />
          </label>
          {uploadStatus !== null && <p className="mt-1 text-xs text-muted">{uploadStatus}</p>}
        </div>
        {uploading && (
          <div className="rounded-lg border border-line bg-surface p-3">
            <div className="flex items-center gap-2 text-xs text-muted">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-success-bg" aria-hidden="true" />
              Processing: upload → extraction → chunking → embedding → ready
            </div>
          </div>
        )}
      </div>
      {isLoading ? (
        <p className="text-sm text-muted">Loading documents…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-muted">No documents found.</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => {
            const versions = doc.versions ?? []
            const latest = versions[0]
            return (
              <li key={doc.document_id} className="rounded-lg border border-line bg-surface px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 basis-full sm:basis-0">
                    <span className="text-sm font-medium text-content break-words block">
                      {latest?.original_filename ?? 'Untitled'}
                    </span>
                    <p className="mt-1 text-xs text-muted">
                      {versions.length} version{versions.length !== 1 ? 's' : ''} · {latest?.file_type ?? 'unknown'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="cursor-pointer rounded border border-control bg-surface px-2 py-1 text-xs text-content hover:bg-hover">
                      New version
                      <input
                        type="file"
                        className="hidden"
                        onChange={(e) => void handleNewVersion(e, doc.document_id)}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.document_id)}
                      className="shrink-0 rounded border border-danger bg-danger-bg px-2 py-1 text-xs text-danger hover:bg-danger-bg"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

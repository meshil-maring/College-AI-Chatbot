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
      <h2 className="text-xl font-bold text-white">Documents</h2>
      {error !== null && (
        <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-3">
        <label className="block">
          <span className="text-xs text-slate-400">Knowledge Source</span>
          {institutionId === null ? (
            <p role="status" className="mt-1 text-sm text-slate-400">
              No institution is linked to your administrator account, so there are no knowledge sources to manage yet.
            </p>
          ) : isSourcesLoading ? (
            <p className="mt-1 text-sm text-slate-400">Loading knowledge sources…</p>
          ) : sourcesError !== null ? (
            <div className="mt-1 space-y-2">
              <p role="alert" className="text-sm text-red-300">
                {sourcesError}
              </p>
              <button
                type="button"
                onClick={() => void loadSources()}
                className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                Retry
              </button>
            </div>
          ) : knowledgeSources.length === 0 ? (
            <div className="mt-1 space-y-2">
              <p className="text-sm text-slate-400">No knowledge sources yet. Create one to upload documents.</p>
              <button
                type="button"
                onClick={() => void handleCreateKnowledgeSource()}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                New Knowledge Source
              </button>
            </div>
          ) : (
            <div className="mt-1 flex gap-2">
              <select
                value={knowledgeSourceId}
                onChange={(e) => setKnowledgeSourceId(e.target.value)}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
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
                className="shrink-0 rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                +
              </button>
            </div>
          )}
        </label>
        <div>
          <label className="block">
            <span className="text-xs text-slate-400">Upload Document</span>
            <input
              type="file"
              onChange={handleUpload}
              disabled={uploading || knowledgeSourceId.trim().length === 0}
              className="mt-1 block w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-emerald-500 disabled:file:opacity-50"
            />
          </label>
          {uploadStatus !== null && <p className="mt-1 text-xs text-slate-400">{uploadStatus}</p>}
        </div>
        {uploading && (
          <div className="rounded-lg border border-slate-700 bg-slate-900 p-3">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-400" aria-hidden="true" />
              Processing: upload → extraction → chunking → embedding → ready
            </div>
          </div>
        )}
      </div>
      {isLoading ? (
        <p className="text-sm text-slate-400">Loading documents…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-slate-400">No documents found.</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => {
            const versions = doc.versions ?? []
            const latest = versions[0]
            return (
              <li key={doc.document_id} className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-white truncate block">
                      {latest?.original_filename ?? 'Untitled'}
                    </span>
                    <p className="mt-1 text-xs text-slate-400">
                      {versions.length} version{versions.length !== 1 ? 's' : ''} · {latest?.file_type ?? 'unknown'}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <label className="cursor-pointer rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700">
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
                      className="shrink-0 rounded border border-red-900/50 bg-red-500/10 px-2 py-1 text-xs text-red-300 hover:bg-red-500/20"
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

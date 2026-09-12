/**
 * Phase Admin-4 — Document manager.
 *
 * Upload documents to knowledge sources and manage existing documents.
 * Shows processing status: upload → extraction → chunking → embedding → ready/error.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import {
  createKnowledgeSource,
  deleteDocument,
  listDocuments,
  listKnowledgeSources,
  uploadDocument,
  uploadDocumentVersion,
} from '../../services/adminApi.ts'
import type { DocumentWithVersions, KnowledgeSource } from '../../types/admin.ts'

/** Demo institution seeded in the database (see Admin-1 fixtures). */
const DEMO_INSTITUTION_ID = '30000000-0000-0000-0000-000000000001'

export default function DocumentManager() {
  const { accessToken } = useAuth()
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([])
  const [isSourcesLoading, setIsSourcesLoading] = useState(true)
  const [sourcesError, setSourcesError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<DocumentWithVersions[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [knowledgeSourceId, setKnowledgeSourceId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)

  const loadSources = useCallback(async () => {
    if (accessToken === null) return
    setIsSourcesLoading(true)
    setSourcesError(null)
    try {
      const data = await listKnowledgeSources(accessToken, DEMO_INSTITUTION_ID)
      setKnowledgeSources(data)
      // Auto-select the first knowledge source so the upload control is
      // usable immediately (previously it stayed disabled on an empty ID).
      setKnowledgeSourceId((prev) => {
        if (prev.trim().length > 0) return prev
        return data.length > 0 ? data[0].knowledge_source_id : prev
      })
    } catch (err) {
      setSourcesError(err instanceof Error ? err.message : 'Failed to load knowledge sources.')
    } finally {
      setIsSourcesLoading(false)
    }
  }, [accessToken])

  useEffect(() => {
    void loadSources()
  }, [loadSources])

  const load = useCallback(async () => {
    if (accessToken === null || knowledgeSourceId.trim().length === 0) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listDocuments(accessToken, knowledgeSourceId.trim())
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, knowledgeSourceId])

  useEffect(() => {
    if (knowledgeSourceId.trim().length > 0) void load()
  }, [load, knowledgeSourceId])

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (accessToken === null) return
    const file = e.target.files?.[0]
    if (file === undefined) return
    if (knowledgeSourceId.trim().length === 0) {
      setError('Select a knowledge source before uploading.')
      return
    }
    setUploading(true)
    setUploadStatus('Uploading…')
    setError(null)
    try {
      await uploadDocument(accessToken, knowledgeSourceId.trim(), file)
      setUploadStatus('Processing: extraction → chunking → embedding…')
      window.setTimeout(() => {
        void load()
        setUploadStatus('Document uploaded successfully.')
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload document.')
      setUploadStatus('Upload failed.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }, [accessToken, knowledgeSourceId, load])

  const handleNewVersion = useCallback(async (e: React.ChangeEvent<HTMLInputElement>, documentId: string) => {
    if (accessToken === null) return
    const file = e.target.files?.[0]
    if (file === undefined) return
    setUploading(true)
    setUploadStatus('Uploading new version…')
    setError(null)
    try {
      await uploadDocumentVersion(accessToken, documentId, file)
      setUploadStatus('Processing new version: extraction → chunking → embedding…')
      window.setTimeout(() => {
        void load()
        setUploadStatus('New version uploaded successfully.')
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload new version.')
      setUploadStatus('Upload failed.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }, [accessToken, load])

  const handleCreateKnowledgeSource = useCallback(async () => {
    if (accessToken === null) return
    const title = window.prompt('Enter a title for the new knowledge source:')
    if (title === null || title.trim().length === 0) return
    setError(null)
    try {
      const created = await createKnowledgeSource(accessToken, {
        institution_id: DEMO_INSTITUTION_ID,
        source_type: 'handbook',
        title: title.trim(),
      })
      setKnowledgeSources((prev) => [created, ...prev])
      setKnowledgeSourceId(created.knowledge_source_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create knowledge source.')
    }
  }, [accessToken])

  const handleDelete = useCallback(async (id: string) => {
    if (accessToken === null) return
    if (!window.confirm('Delete this document?')) return
    try {
      await deleteDocument(accessToken, id)
      setDocuments((prev) => prev.filter((d) => d.document_id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document.')
    }
  }, [accessToken])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-white">Documents</h2>
      {error !== null && <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-3">
        <label className="block">
          <span className="text-xs text-slate-400">Knowledge Source</span>
          {isSourcesLoading ? (
            <p className="mt-1 text-sm text-slate-400">Loading knowledge sources…</p>
          ) : sourcesError !== null ? (
            <div className="mt-1 space-y-2">
              <p role="alert" className="text-sm text-red-300">{sourcesError}</p>
              <button type="button" onClick={() => void loadSources()} className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400">
                Retry
              </button>
            </div>
          ) : knowledgeSources.length === 0 ? (
            <div className="mt-1 space-y-2">
              <p className="text-sm text-slate-400">No knowledge sources yet. Create one to upload documents.</p>
              <button type="button" onClick={() => void handleCreateKnowledgeSource()} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400">
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
              <button type="button" onClick={() => void handleCreateKnowledgeSource()} title="New knowledge source" className="shrink-0 rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400">
                +
              </button>
            </div>
          )}
        </label>
        <div>
          <label className="block">
            <span className="text-xs text-slate-400">Upload Document</span>
            <input type="file" onChange={handleUpload} disabled={uploading || knowledgeSourceId.trim().length === 0} className="mt-1 block w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-emerald-500 file:disabled:opacity-50" />
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
                  <span className="text-sm font-medium text-white truncate block">{latest?.original_filename ?? 'Untitled'}</span>
                  <p className="mt-1 text-xs text-slate-400">{versions.length} version{versions.length !== 1 ? 's' : ''} · {latest?.file_type ?? 'unknown'}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <label className="cursor-pointer rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700">
                    New version
                    <input type="file" className="hidden" onChange={(e) => void handleNewVersion(e, doc.document_id)} />
                  </label>
                  <button type="button" onClick={() => handleDelete(doc.document_id)} className="shrink-0 rounded border border-red-900/50 bg-red-500/10 px-2 py-1 text-xs text-red-300 hover:bg-red-500/20">Delete</button>
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

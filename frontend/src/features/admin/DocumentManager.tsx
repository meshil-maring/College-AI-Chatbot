/**
 * Phase Admin-4 — Document manager.
 *
 * Upload documents to knowledge sources and manage existing documents.
 * Shows processing status: upload → extraction → chunking → embedding → ready/error.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
} from '../../services/adminApi.ts'
import type { DocumentWithVersions } from '../../types/admin.ts'

export default function DocumentManager() {
  const { accessToken } = useAuth()
  const [documents, setDocuments] = useState<DocumentWithVersions[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [knowledgeSourceId, setKnowledgeSourceId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)

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
      setError('Enter a knowledge source ID before uploading.')
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
          <span className="text-xs text-slate-400">Knowledge Source ID</span>
          <input type="text" value={knowledgeSourceId} onChange={(e) => setKnowledgeSourceId(e.target.value)} placeholder="Enter knowledge source UUID" className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
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
      {knowledgeSourceId.trim().length === 0 ? (
        <p className="text-sm text-slate-400">Enter a knowledge source ID to view documents.</p>
      ) : isLoading ? (
        <p className="text-sm text-slate-400">Loading documents…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-slate-400">No documents found.</p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li key={doc.document_id} className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-white truncate block">{doc.versions[0]?.original_filename ?? 'Untitled'}</span>
                  <p className="mt-1 text-xs text-slate-400">{doc.versions.length} version{doc.versions.length !== 1 ? 's' : ''} · {doc.versions[0]?.file_type ?? 'unknown'}</p>
                </div>
                <button type="button" onClick={() => handleDelete(doc.document_id)} className="shrink-0 rounded border border-red-900/50 bg-red-500/10 px-2 py-1 text-xs text-red-300 hover:bg-red-500/20">Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import {
  createKnowledgeSource,
  deleteDocument,
  listDocuments,
  listKnowledgeSources,
  uploadDocument,
  uploadDocumentVersion,
} from '../../../services/admin/adminApi.ts'
import type { DocumentWithVersions, KnowledgeSource } from '../../../types/admin.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
export function useDocumentManager() {
  const { accessToken, user } = useAuth()
  // Tenant context resolved SERVER-SIDE (never hardcoded or guessed).
  const institutionId = user?.institution_id ?? null
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
    if (accessToken === null || institutionId === null) return
    setIsSourcesLoading(true)
    setSourcesError(null)
    try {
      const data = await listKnowledgeSources(accessToken, institutionId)
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
  }, [accessToken, institutionId])

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

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
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
    },
    [accessToken, knowledgeSourceId, load],
  )

  const handleNewVersion = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>, documentId: string) => {
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
    },
    [accessToken, load],
  )

  const handleCreateKnowledgeSource = useCallback(async () => {
    if (accessToken === null || institutionId === null) return
    const title = window.prompt('Enter a title for the new knowledge source:')
    if (title === null || title.trim().length === 0) return
    setError(null)
    try {
      const created = await createKnowledgeSource(accessToken, {
        institution_id: institutionId,
        source_type: 'handbook',
        title: title.trim(),
      })
      setKnowledgeSources((prev) => [created, ...prev])
      setKnowledgeSourceId(created.knowledge_source_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create knowledge source.')
    }
  }, [accessToken, institutionId])

  const handleDelete = useCallback(
    async (id: string) => {
      if (accessToken === null) return
      if (!window.confirm('Delete this document?')) return
      try {
        await deleteDocument(accessToken, id)
        setDocuments((prev) => prev.filter((d) => d.document_id !== id))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete document.')
      }
    },
    [accessToken],
  )

  return {
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
  }
}

export type DocumentManagerModel = ReturnType<typeof useDocumentManager>

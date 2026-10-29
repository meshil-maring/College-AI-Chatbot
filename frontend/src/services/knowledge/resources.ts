import type {
  LearningResource,
  ResourceDecision,
  ResourceFields,
  ResourcePage,
  ResourceRevision,
  ResourceView,
  ReviewAction,
} from '../../types/learningResources.ts'
import { API_BASE_URL, AdminApiError, requestJson } from '../admin/http.ts'
import type { ResourceChatContext } from '../../types/chat.ts'

const BASE = `${API_BASE_URL}/v1/knowledge`
export { AdminApiError as ResourceApiError } from '../admin/http.ts'

export function getResourceChatContext(token: string, sourceId: string, signal?: AbortSignal) {
  return requestJson<ResourceChatContext>(
    'GET',
    `${BASE}/resources/${encodeURIComponent(sourceId)}/chat-context`,
    token,
    undefined,
    signal,
  )
}

/** The shared transport retains token-scoped 401 handling and multipart headers. */
export function listResources(token: string, view: ResourceView, offset: number, signal?: AbortSignal) {
  const path = view === 'library' ? 'resources' : `revisions?view=${view}`
  const separator = path.includes('?') ? '&' : '?'
  return requestJson<ResourcePage<LearningResource | ResourceRevision>>(
    'GET',
    `${BASE}/${path}${separator}limit=20&offset=${offset}`,
    token,
    undefined,
    signal,
  )
}
export function getResource(token: string, id: string, signal?: AbortSignal) {
  return requestJson<LearningResource>('GET', `${BASE}/resources/${encodeURIComponent(id)}`, token, undefined, signal)
}
export function getRevision(token: string, id: string, signal?: AbortSignal) {
  return requestJson<ResourceRevision>('GET', `${BASE}/revisions/${encodeURIComponent(id)}`, token, undefined, signal)
}
export function createResource(token: string, fields: ResourceFields) {
  return requestJson<ResourceRevision>('POST', `${BASE}/resources`, token, fields)
}
export function createRevision(token: string, source: string) {
  return requestJson<ResourceRevision>('POST', `${BASE}/resources/${encodeURIComponent(source)}/revisions`, token, {})
}
export function saveRevision(
  token: string,
  revision: ResourceRevision,
  fields: ResourceFields,
  expectedVersion: number,
) {
  return requestJson<ResourceRevision>(
    'PATCH',
    `${BASE}/resources/${encodeURIComponent(revision.knowledge_source_id)}/revisions/${encodeURIComponent(revision.revision_id)}`,
    token,
    { ...fields, expected_version: expectedVersion },
  )
}
export function uploadResourceFile(token: string, revision: ResourceRevision, file: File, documentId?: string) {
  const body = new FormData()
  body.append('file', file)
  body.append('expected_version', String(revision.revision_version))
  if (documentId) body.append('document_id', documentId)
  return requestJson<ResourceRevision>(
    'POST',
    `${BASE}/revisions/${encodeURIComponent(revision.revision_id)}/documents`,
    token,
    body,
  )
}
export function retryResourceIndex(token: string, revision: ResourceRevision, versionId: string) {
  return requestJson<ResourceRevision>(
    'POST',
    `${BASE}/revisions/${encodeURIComponent(revision.revision_id)}/retry-index`,
    token,
    {
      expected_version: revision.revision_version,
      document_version_id: versionId,
    },
  )
}
export function decideRevision(token: string, revision: ResourceRevision, action: ReviewAction, notes: string) {
  const command: ResourceDecision = { expected_version: revision.revision_version }
  if (action === 'publish' || action === 'unpublish') command.expected_policy = revision.policy_version
  if (notes.trim()) command.notes = notes.trim()
  return requestJson<ResourceRevision>(
    'POST',
    `${BASE}/revisions/${encodeURIComponent(revision.revision_id)}/${action}`,
    token,
    command,
  )
}
export function resourceError(error: unknown): string {
  if (error instanceof AdminApiError) {
    if (error.code === 'RESOURCE_INDEXING_FAILED')
      return 'Your file was saved, but indexing failed. Refresh the draft to retry indexing.'
    if (error.status === 409)
      return 'This resource changed. Your entries are kept. Reload the latest revision before continuing.'
    if (error.status === 401 || error.status === 403)
      return 'Your access to learning resources changed. Reload your session to continue.'
    if (error.status === 404) return 'This resource is no longer available.'
    if (error.status === 422)
      return 'The change could not be saved. Check the audience, review state and indexing status.'
    if (error.status === 503) return 'Learning resources are temporarily unavailable. Please try again later.'
  }
  return 'The request could not be confirmed. Your entries are kept. Refresh before trying again.'
}

import type {
  DocumentWithVersions,
  Faq,
  FaqCreate,
  FaqUpdate,
  KnowledgeSource,
  KnowledgeSourceCreate,
  KnowledgeSourceUpdate,
  Notice,
  NoticeCreate,
  NoticeUpdate,
} from '../../types/admin.ts'
import { ADMIN_BASE, requestJson } from './http.ts'
// ============================================================================
// Knowledge sources + Documents
// ============================================================================

export async function listKnowledgeSources(accessToken: string, institutionId: string): Promise<KnowledgeSource[]> {
  return requestJson<KnowledgeSource[]>(
    'GET',
    `${ADMIN_BASE}/knowledge-sources?institution_id=${encodeURIComponent(institutionId)}`,
    accessToken,
  )
}

export async function createKnowledgeSource(
  accessToken: string,
  payload: KnowledgeSourceCreate,
): Promise<KnowledgeSource> {
  return requestJson<KnowledgeSource>('POST', `${ADMIN_BASE}/knowledge-sources`, accessToken, payload)
}

export async function updateKnowledgeSource(
  accessToken: string,
  id: string,
  payload: KnowledgeSourceUpdate,
): Promise<KnowledgeSource> {
  return requestJson<KnowledgeSource>('PATCH', `${ADMIN_BASE}/knowledge-sources/${id}`, accessToken, payload)
}

export async function listDocuments(accessToken: string, knowledgeSourceId: string): Promise<DocumentWithVersions[]> {
  return requestJson<DocumentWithVersions[]>(
    'GET',
    `${ADMIN_BASE}/knowledge-sources/${knowledgeSourceId}/documents`,
    accessToken,
  )
}

export async function uploadDocument(accessToken: string, knowledgeSourceId: string, file: File): Promise<unknown> {
  const formData = new FormData()
  formData.append('knowledge_source_id', knowledgeSourceId)
  formData.append('file', file)
  return requestJson<unknown>('POST', `${ADMIN_BASE}/documents`, accessToken, formData)
}

export async function uploadDocumentVersion(accessToken: string, documentId: string, file: File): Promise<unknown> {
  const formData = new FormData()
  formData.append('file', file)
  return requestJson<unknown>('POST', `${ADMIN_BASE}/documents/${documentId}/versions`, accessToken, formData)
}

export async function deleteDocument(accessToken: string, documentId: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/documents/${documentId}`, accessToken)
}

// ============================================================================
// FAQs
// ============================================================================

export async function listFaqs(accessToken: string, institutionId?: string): Promise<Faq[]> {
  const params = institutionId ? `?institution_id=${encodeURIComponent(institutionId)}` : ''
  return requestJson<Faq[]>('GET', `${ADMIN_BASE}/faqs${params}`, accessToken)
}

export async function createFaq(accessToken: string, payload: FaqCreate): Promise<Faq> {
  return requestJson<Faq>('POST', `${ADMIN_BASE}/faqs`, accessToken, payload)
}

export async function updateFaq(accessToken: string, id: string, payload: FaqUpdate): Promise<Faq> {
  return requestJson<Faq>('PATCH', `${ADMIN_BASE}/faqs/${id}`, accessToken, payload)
}

export async function deleteFaq(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/faqs/${id}`, accessToken)
}

// ============================================================================
// Notices
// ============================================================================

export async function listNotices(accessToken: string, institutionId?: string): Promise<Notice[]> {
  const params = institutionId ? `?institution_id=${encodeURIComponent(institutionId)}` : ''
  return requestJson<Notice[]>('GET', `${ADMIN_BASE}/notices${params}`, accessToken)
}

export async function createNotice(accessToken: string, payload: NoticeCreate): Promise<Notice> {
  return requestJson<Notice>('POST', `${ADMIN_BASE}/notices`, accessToken, payload)
}

export async function updateNotice(accessToken: string, id: string, payload: NoticeUpdate): Promise<Notice> {
  return requestJson<Notice>('PATCH', `${ADMIN_BASE}/notices/${id}`, accessToken, payload)
}

export async function deleteNotice(accessToken: string, id: string): Promise<void> {
  await requestJson<{ deleted: boolean }>('DELETE', `${ADMIN_BASE}/notices/${id}`, accessToken)
}

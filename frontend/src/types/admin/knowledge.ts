/**
 * Phase Admin-4 — Admin module frontend types.
 *
 * Typed mirror of the backend admin API contracts (backend/app/schemas/admin/admin.py
 * and backend/app/api/admin.py). Only fields the backend actually returns are
 * declared. These types are consumed by adminApi.ts and the admin feature
 * components.
 */

// ============================================================================
// Knowledge sources
// ============================================================================

export interface KnowledgeSource {
  knowledge_source_id: string
  institution_id: string
  source_type: string
  title: string
  description: string | null
  authority_level: string
  lifecycle_status: string
  effective_from: string | null
  effective_until: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeSourceCreate {
  institution_id: string
  source_type: string
  title: string
  description?: string | null
  authority_level?: string
  lifecycle_status?: string
  effective_from?: string | null
  effective_until?: string | null
}

export interface KnowledgeSourceUpdate {
  title?: string | null
  description?: string | null
  authority_level?: string | null
  lifecycle_status?: string | null
  effective_from?: string | null
  effective_until?: string | null
}

// ============================================================================
// Documents and versions
// ============================================================================

export interface DocumentVersion {
  document_version_id: string
  document_id: string
  version_number: number
  version_label: string | null
  original_filename: string
  file_type: string
  mime_type: string | null
  file_size_bytes: number | null
  storage_bucket: string
  storage_object_key: string
  file_checksum: string | null
  lifecycle_status: string
  supersedes_version_id: string | null
  created_by_user_id: string
  created_at: string
  updated_at: string
}

export interface DocumentWithVersions {
  document_id: string
  knowledge_source_id: string
  created_at: string
  updated_at: string
  versions: DocumentVersion[]
}

// ============================================================================
// FAQs
// ============================================================================

export interface Faq {
  faq_id: string
  institution_id: string | null
  category: string
  question: string
  answer: string
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FaqCreate {
  institution_id?: string | null
  category?: string
  question: string
  answer: string
  display_order?: number
  is_active?: boolean
}

export interface FaqUpdate {
  category?: string | null
  question?: string | null
  answer?: string | null
  display_order?: number | null
  is_active?: boolean | null
}

// ============================================================================
// Notices
// ============================================================================

export interface Notice {
  notice_id: string
  institution_id: string | null
  title: string
  content: string
  category: string
  priority: string
  is_active: boolean
  is_pinned: boolean
  published_at: string | null
  expires_at: string | null
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface NoticeCreate {
  institution_id?: string | null
  title: string
  content: string
  category?: string
  priority?: string
  is_active?: boolean
  is_pinned?: boolean
  published_at?: string | null
  expires_at?: string | null
}

export interface NoticeUpdate {
  title?: string | null
  content?: string | null
  category?: string | null
  priority?: string | null
  is_active?: boolean | null
  is_pinned?: boolean | null
  published_at?: string | null
  expires_at?: string | null
}

/** Shared contracts for /api/v1/knowledge; identity and publication are server-owned. */
export type AudienceRole = 'student' | 'staff' | 'faculty' | 'admin'
export interface ResourceAudience {
  mode: 'public' | 'institution' | 'roles'
  roles: AudienceRole[]
}
export interface ResourceFields {
  title: string
  source_type: string
  description: string | null
  audience: ResourceAudience
  effective_from: string | null
  effective_until: string | null
}
export interface ResourceFile {
  document_id: string
  document_version_id: string
  original_filename: string
  file_type: string
  version_number: number
  file_size_bytes: number | null
  indexing_status: 'queued' | 'processing' | 'indexed' | 'failed' | null
}
export interface LearningResource {
  knowledge_source_id: string
  title: string
  description: string | null
  source_type: string
  visibility: 'public' | 'authenticated' | 'restricted'
  effective_from: string | null
  effective_until: string | null
  policy_version: number
  audience_roles: AudienceRole[]
  documents: ResourceFile[]
}
export interface ResourceRevision extends LearningResource {
  revision_id: string
  institution_id: string
  revision_number: number
  revision_version: number
  lifecycle_status: 'draft' | 'under_review' | 'approved' | 'published' | 'archived' | 'superseded'
  created_by_user_id: string
  reviewed_by_user_id: string | null
  approved_by_user_id: string | null
  review_notes: string | null
  created_at: string
  updated_at: string
}
export interface ResourcePage<T> {
  items: T[]
  total: number
}
export type ResourceView = 'library' | 'own' | 'review'
export type ReviewAction = 'submit' | 'request_changes' | 'approve' | 'publish' | 'unpublish'
export interface ResourceDecision {
  expected_version: number
  expected_policy?: number
  notes?: string
}

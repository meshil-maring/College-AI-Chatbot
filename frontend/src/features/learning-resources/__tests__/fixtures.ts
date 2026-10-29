import type { CurrentUser } from '../../../types/auth.ts'
import type { LearningResource, ResourceRevision } from '../../../types/learningResources.ts'

export function user(role: CurrentUser['role'] = 'faculty'): CurrentUser {
  return {
    authenticated: true,
    user_id: 'user-a',
    auth_user_id: 'auth-a',
    email: 'reader@example.invalid',
    institution_id: 'college-a',
    role,
    effective_permissions: ['*'],
  }
}
export function draft(overrides: Partial<ResourceRevision> = {}): ResourceRevision {
  return {
    knowledge_source_id: 'source-a',
    title: 'Library guide',
    description: 'Borrowing information',
    source_type: 'handbook',
    visibility: 'restricted',
    audience_roles: ['student'],
    effective_from: null,
    effective_until: null,
    policy_version: 0,
    documents: [],
    revision_id: 'revision-a',
    institution_id: 'college-a',
    revision_number: 1,
    revision_version: 4,
    lifecycle_status: 'draft',
    created_by_user_id: 'user-a',
    reviewed_by_user_id: null,
    approved_by_user_id: null,
    review_notes: null,
    created_at: '2026-10-28T10:00:00Z',
    updated_at: '2026-10-28T10:00:00Z',
    ...overrides,
  }
}
export function indexedFiles(): ResourceRevision['documents'] {
  return [
    {
      document_id: 'document-a',
      document_version_id: 'version-a',
      original_filename: 'guide.txt',
      file_type: 'txt',
      version_number: 1,
      file_size_bytes: 1024,
      indexing_status: 'indexed',
    },
  ]
}
export function published(): LearningResource {
  return {
    knowledge_source_id: 'published-source',
    title: 'Published handbook',
    description: 'Official library information',
    source_type: 'handbook',
    visibility: 'public',
    audience_roles: [],
    documents: indexedFiles(),
    policy_version: 1,
    effective_from: null,
    effective_until: null,
  }
}

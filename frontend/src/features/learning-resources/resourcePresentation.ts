import type { AudienceRole, LearningResource, ResourceRevision } from '../../types/learningResources.ts'

export const audienceRoles: { value: AudienceRole; label: string }[] = [
  { value: 'student', label: 'Students' },
  { value: 'staff', label: 'Staff' },
  { value: 'faculty', label: 'Teachers' },
  { value: 'admin', label: 'Admins' },
]
export const stateLabels: Record<ResourceRevision['lifecycle_status'], string> = {
  draft: 'Draft',
  under_review: 'Under review',
  approved: 'Approved',
  published: 'Published',
  archived: 'Archived',
  superseded: 'Superseded',
}
export function audienceLabel(resource: Pick<LearningResource, 'visibility' | 'audience_roles'>) {
  if (resource.visibility === 'public') return 'Public'
  if (resource.visibility === 'authenticated') return 'Institution members'
  return (
    audienceRoles
      .filter((role) => resource.audience_roles.includes(role.value))
      .map((role) => role.label)
      .join(' + ') || 'Audience not selected'
  )
}
export function typeLabel(value: string) {
  const label = value.replace(/[_-]+/g, ' ')
  return label.charAt(0).toUpperCase() + label.slice(1)
}
export function fileSize(bytes: number | null) {
  if (bytes === null) return 'Size unavailable'
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
export function isReady(resource: LearningResource) {
  return resource.documents.length > 0 && resource.documents.every((file) => file.indexing_status === 'indexed')
}
export function indexState(resource: LearningResource) {
  if (resource.documents.some((file) => file.indexing_status === 'failed')) return 'failed'
  if (resource.documents.some((file) => file.indexing_status === 'processing')) return 'processing'
  if (resource.documents.some((file) => file.indexing_status === 'queued')) return 'queued'
  return isReady(resource) ? 'indexed' : null
}

import { Globe2, LockKeyhole, Users } from 'lucide-react'
import type { LearningResource, ResourceRevision } from '../../types/learningResources.ts'
import { audienceLabel, stateLabels } from './resourcePresentation.ts'

export function AudienceBadge({ resource }: { resource: LearningResource }) {
  const Icon = resource.visibility === 'public' ? Globe2 : resource.visibility === 'authenticated' ? Users : LockKeyhole
  return (
    <span className="lr-badge lr-neutral">
      <Icon aria-hidden="true" />
      {audienceLabel(resource)}
    </span>
  )
}
export function RevisionBadge({ status }: { status: ResourceRevision['lifecycle_status'] }) {
  const color =
    {
      draft: 'neutral',
      under_review: 'warning',
      approved: 'info',
      published: 'success',
      archived: 'neutral',
      superseded: 'neutral',
    }[status] ?? 'neutral'
  return <span className={`lr-badge lr-${color}`}>{stateLabels[status] ?? 'Unavailable'}</span>
}
export function IndexBadge({ status }: { status: string | null }) {
  const labels: Record<string, string> = {
    queued: 'Queued',
    processing: 'Indexing',
    indexed: 'Indexed',
    failed: 'Indexing failed',
  }
  const color = status === 'indexed' ? 'success' : status === 'failed' ? 'danger' : 'neutral'
  return <span className={`lr-badge lr-${color}`}>{labels[status ?? ''] ?? 'Indexing unavailable'}</span>
}

/** Phase 6.16 — Learning resources (read-only, authorized subset only). */

import type { StudentResourceList } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock } from './SectionState.tsx'
import { formatDate, formatLabel } from './studentFormat.ts'

const EMPTY_MESSAGE = 'No learning resources are currently available.'
const ERROR_MESSAGE = 'Unable to load learning resources.'

export default function ResourcesPanel({
  resources,
  compact = false,
}: {
  resources: StudentResourceState<StudentResourceList>
  compact?: boolean
}) {
  if (resources.status === 'loading' || resources.status === 'idle') {
    return <LoadingBlock label="Loading learning resources…" />
  }
  if (resources.status === 'error') {
    return <ErrorBlock message={resources.error ?? ERROR_MESSAGE} onRetry={resources.reload} />
  }
  const items = resources.data?.items ?? []
  const visible = compact ? items.slice(0, 4) : items
  if (visible.length === 0) return <EmptyBlock message={EMPTY_MESSAGE} />
  return (
    <ul className="space-y-3">
      {visible.map((resource) => (
        <li key={resource.resource_id} className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
          <p className="text-sm font-medium text-white">{resource.title}</p>
          {resource.description?.trim() ? (
            <p className="mt-1 text-sm text-slate-300">{resource.description}</p>
          ) : null}
          <p className="mt-1 text-xs text-slate-500">
            {formatLabel(resource.source_type)} · Effective from {formatDate(resource.effective_from)}
          </p>
        </li>
      ))}
    </ul>
  )
}

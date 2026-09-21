/** Phase 6.16 — Learning resources (read-only, authorized subset only). */

import type { StudentResourceList } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock } from './SectionState.tsx'
import { formatDate, formatLabel, formatText } from './studentFormat.ts'

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
  const rawItems = resources.data?.items
  const items = Array.isArray(rawItems) ? rawItems : []
  // Phase 6.16.1: the server is authoritative for dashboard limits (limit=6)
  // and ordering (newest first). Render every returned row — no client-side
  // slicing that could change server-defined semantics.
  const visible = compact ? items : items
  if (visible.length === 0) return <EmptyBlock message={EMPTY_MESSAGE} />
  return (
    <ul className="space-y-3">
      {visible.map((resource, index) => (
        <li
          key={`${typeof resource?.resource_id === 'string' ? resource.resource_id : 'resource'}-${index}`}
          className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2"
        >
          <p className="break-words text-sm font-medium text-white">{formatText(resource?.title)}</p>
          {typeof resource?.description === 'string' && resource.description.trim() ? (
            <p className="mt-1 break-words text-sm text-slate-300">{resource.description}</p>
          ) : null}
          <p className="mt-1 break-words text-xs text-slate-500">
            {formatLabel(resource?.source_type)} · Effective from{' '}
            {formatDate(typeof resource?.effective_from === 'string' ? resource.effective_from : null)}
          </p>
        </li>
      ))}
    </ul>
  )
}

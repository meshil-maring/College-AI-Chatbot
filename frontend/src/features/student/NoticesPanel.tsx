/** Phase 6.16 — Recent notices (read-only, tenant-scoped server-side). */

import type { StudentNoticeList } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock } from './SectionState.tsx'
import { formatDate, formatLabel, formatText } from './studentFormat.ts'

const EMPTY_MESSAGE = 'No recent notices.'
const ERROR_MESSAGE = 'Unable to load notices.'

export default function NoticesPanel({
  notices,
  compact = false,
}: {
  notices: StudentResourceState<StudentNoticeList>
  compact?: boolean
}) {
  if (notices.status === 'loading' || notices.status === 'idle') {
    return <LoadingBlock label="Loading notices…" />
  }
  if (notices.status === 'error') {
    return <ErrorBlock message={notices.error ?? ERROR_MESSAGE} onRetry={notices.reload} />
  }
  const rawItems = notices.data?.items
  const items = Array.isArray(rawItems) ? rawItems : []
  // Phase 6.16.1: the server is authoritative for dashboard limits (limit=5)
  // and ordering (pinned first, then newest). The dashboard renders every
  // row the backend returned — no client-side slicing that could hide rows
  // or change server-defined semantics.
  const visible = compact ? items : items
  if (visible.length === 0) return <EmptyBlock message={EMPTY_MESSAGE} />
  return (
    <ul className="space-y-3">
      {visible.map((notice, index) => (
        <li
          key={`${typeof notice?.notice_id === 'string' ? notice.notice_id : 'notice'}-${index}`}
          className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2"
        >
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <p className="min-w-0 flex-1 break-words text-sm font-medium text-white">
              {formatText(notice?.title)}
            </p>
            {notice?.is_pinned === true ? (
              <span className="shrink-0 rounded-full border border-amber-700/60 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">
                Pinned
              </span>
            ) : null}
          </div>
          <p className="mt-1 break-words text-sm text-slate-300">{formatText(notice?.content)}</p>
          <p className="mt-1 break-words text-xs text-slate-500">
            {formatLabel(notice?.category)} · {formatLabel(notice?.priority)} ·{' '}
            {formatDate(typeof notice?.published_at === 'string' ? notice.published_at : null)}
          </p>
        </li>
      ))}
    </ul>
  )
}

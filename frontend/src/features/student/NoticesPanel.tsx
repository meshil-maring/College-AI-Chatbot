/** Phase 6.16 — Recent notices (read-only, tenant-scoped server-side). */

import type { StudentNoticeList } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock } from './SectionState.tsx'
import { formatDate, formatLabel } from './studentFormat.ts'

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
  const items = notices.data?.items ?? []
  const visible = compact ? items.slice(0, 3) : items
  if (visible.length === 0) return <EmptyBlock message={EMPTY_MESSAGE} />
  return (
    <ul className="space-y-3">
      {visible.map((notice) => (
        <li key={notice.notice_id} className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-white">{notice.title}</p>
            {notice.is_pinned ? (
              <span className="rounded-full border border-amber-700/60 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">
                Pinned
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-slate-300">{notice.content}</p>
          <p className="mt-1 text-xs text-slate-500">
            {formatLabel(notice.category)} · {formatLabel(notice.priority)} · {formatDate(notice.published_at)}
          </p>
        </li>
      ))}
    </ul>
  )
}

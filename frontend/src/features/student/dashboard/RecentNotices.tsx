/** The three most recent published notices, linking to the Notices page. */

import { CalendarDays, FileText, Megaphone, ShieldCheck, type LucideIcon } from 'lucide-react'
import { getMyNotices } from '../../../services/students/studentApi.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../shared/SectionState.tsx'
import { formatText } from '../shared/studentFormat.ts'
import { DashboardPanel, ViewAllButton } from './DashboardPanel.tsx'

const NOTICE_LIMIT = 3

function iconFor(category: string): LucideIcon {
  const value = category.toLowerCase()
  if (value.includes('exam') || value.includes('event') || value.includes('academic')) return CalendarDays
  if (value.includes('hostel') || value.includes('rule') || value.includes('policy')) return ShieldCheck
  return FileText
}

function shortDate(value: string | null): string {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function NoticeList() {
  const notices = useStudentResource(
    (token) => getMyNotices(token, NOTICE_LIMIT),
    'Unable to load notices.',
    '',
    'dashboard-notices',
  )
  if (notices.status === 'loading' || notices.status === 'idle') return <LoadingBlock label="Loading notices…" />
  if (notices.status === 'error')
    return <ErrorBlock message={notices.error ?? 'Unable to load notices.'} onRetry={notices.reload} />
  const items = Array.isArray(notices.data?.items) ? notices.data.items : []
  if (items.length === 0) return <EmptyBlock message="No recent notices." />
  return (
    <ul className="divide-y divide-line">
      {items.map((notice) => {
        const Icon = iconFor(typeof notice.category === 'string' ? notice.category : '')
        return (
          <li key={notice.notice_id} className="flex min-w-0 gap-3 py-3 first:pt-0 last:pb-0">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-warning-bg text-accent">
              <Icon aria-hidden="true" className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 items-start justify-between gap-2">
                <p className="min-w-0 break-words text-sm font-semibold text-content">{formatText(notice.title)}</p>
                <span className="shrink-0 text-xs text-muted">{shortDate(notice.published_at)}</span>
              </div>
              <p className="mt-1 line-clamp-2 break-words text-sm text-muted">{formatText(notice.content)}</p>
            </div>
          </li>
        )
      })}
    </ul>
  )
}

export default function RecentNotices({ enabled, onViewAll }: { enabled: boolean; onViewAll: () => void }) {
  return (
    <DashboardPanel
      icon={Megaphone}
      title="Recent Notices"
      headingId="dashboard-notices"
      action={enabled ? <ViewAllButton onClick={onViewAll} /> : undefined}
    >
      {enabled ? <NoticeList /> : <p className="text-sm text-muted">Notices are unavailable for this account.</p>}
    </DashboardPanel>
  )
}

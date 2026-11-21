import { CheckCircle2, Clock, Eye, Inbox, XCircle, type LucideIcon } from 'lucide-react'
import type { TransferStatus } from '../../../types/transfer.ts'
import { TRANSFER_STATUS_LABEL } from '../transferLabels.ts'
import type { ReviewTab } from './transferFilters.ts'

const TILES: { status: TransferStatus; Icon: LucideIcon; tone: string }[] = [
  { status: 'submitted', Icon: Inbox, tone: 'text-info' },
  { status: 'under_review', Icon: Eye, tone: 'text-warning' },
  { status: 'approved', Icon: CheckCircle2, tone: 'text-success' },
  { status: 'rejected', Icon: XCircle, tone: 'text-danger' },
  { status: 'cancelled', Icon: Clock, tone: 'text-neutral' },
]

/** Status totals that jump to the matching list, and the Pending/History tabs. */
export default function TransferReviewTabs({
  tab,
  activeStatus,
  counts,
  onTab,
  onStatus,
}: {
  tab: ReviewTab
  activeStatus: TransferStatus | 'all'
  counts: Record<TransferStatus, number>
  onTab: (tab: ReviewTab) => void
  onStatus: (status: TransferStatus) => void
}) {
  const pending = counts.submitted + counts.under_review
  const history = counts.approved + counts.rejected + counts.cancelled
  return (
    <div className="space-y-4">
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" aria-label="Transfer totals">
        {TILES.map(({ status, Icon, tone }) => (
          <li key={status}>
            <button
              type="button"
              aria-pressed={activeStatus === status}
              onClick={() => onStatus(status)}
              className={`ui-panel flex w-full flex-col items-start gap-1 p-3 text-left hover:bg-hover ${
                activeStatus === status ? 'ring-2 ring-accent' : ''
              }`}
            >
              <span className="flex items-center gap-2 text-xs text-muted">
                <Icon size={16} aria-hidden="true" className={tone} />
                {TRANSFER_STATUS_LABEL[status]}
              </span>
              <span className="text-2xl font-bold tabular-nums text-content">{counts[status]}</span>
            </button>
          </li>
        ))}
      </ul>
      <div role="tablist" aria-label="Transfer lists" className="flex gap-2 border-b border-line">
        {(
          [
            ['pending', `Pending (${pending})`],
            ['history', `History (${history})`],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            onClick={() => onTab(value)}
            className={`-mb-px min-h-11 border-b-2 px-4 font-medium ${
              tab === value ? 'border-accent text-content' : 'border-transparent text-muted hover:text-content'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

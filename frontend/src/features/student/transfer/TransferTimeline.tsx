import { useState } from 'react'
import type { TransferRequest, TransferStatus } from '../../../types/transfer.ts'
import TransferSummary from '../../transfers/TransferSummary.tsx'
import { TRANSFER_STATUS_LABEL, formatTransferDate, isOpenTransfer } from '../../transfers/transferLabels.ts'

type HistoryFilter = 'all' | Extract<TransferStatus, 'approved' | 'rejected' | 'cancelled'>
const HISTORY_FILTERS: HistoryFilter[] = ['all', 'approved', 'rejected', 'cancelled']

/** The student's open request first, then their filterable transfer history. */
export default function TransferTimeline({
  requests,
  canCancel,
  busy,
  onCancel,
}: {
  requests: TransferRequest[]
  canCancel: boolean
  busy: boolean
  onCancel: (requestId: string) => void
}) {
  const [filter, setFilter] = useState<HistoryFilter>('all')
  const [confirming, setConfirming] = useState<string | null>(null)
  const open = requests.filter((request) => isOpenTransfer(request.status))
  const history = requests.filter((request) => !isOpenTransfer(request.status))
  const shown = history.filter((request) => filter === 'all' || request.status === filter)
  const count = (value: HistoryFilter) =>
    value === 'all' ? history.length : history.filter((request) => request.status === value).length
  if (!requests.length) return <p className="text-sm text-muted">You have no transfer requests or transfers yet.</p>
  return (
    <div className="space-y-6">
      {open.length > 0 && (
        <section aria-labelledby="transfer-open-title" className="space-y-3">
          <h2 id="transfer-open-title" className="text-section font-semibold text-content">
            Open request
          </h2>
          {open.map((request) => (
            <div key={request.transfer_request_id} className="ui-panel space-y-3 border-l-4 border-l-accent p-4 sm:p-5">
              <p className="text-xs text-muted">Submitted {formatTransferDate(request.submitted_at)}</p>
              <TransferSummary request={request} />
              {canCancel && confirming !== request.transfer_request_id && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setConfirming(request.transfer_request_id)}
                  className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover disabled:opacity-50"
                >
                  Cancel request
                </button>
              )}
              {canCancel && confirming === request.transfer_request_id && (
                <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Confirm cancellation">
                  <span className="text-sm text-content">
                    Cancel this request? You can submit a new one afterwards.
                  </span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setConfirming(null)}
                    className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover"
                  >
                    Keep request
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onCancel(request.transfer_request_id)}
                    className="min-h-11 rounded-lg border border-control px-4 py-2 text-danger hover:bg-hover disabled:opacity-50"
                  >
                    {busy ? 'Cancelling…' : 'Yes, cancel it'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}
      <section aria-labelledby="transfer-history-title" className="space-y-3">
        <h2 id="transfer-history-title" className="text-section font-semibold text-content">
          Transfer history
        </h2>
        {history.length > 0 && (
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter transfer history">
            {HISTORY_FILTERS.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
                className={`min-h-10 rounded-full border px-3 text-sm ${
                  filter === value ? 'border-accent bg-accent text-ink' : 'border-control hover:bg-hover'
                }`}
              >
                {value === 'all' ? 'All' : TRANSFER_STATUS_LABEL[value]} ({count(value)})
              </button>
            ))}
          </div>
        )}
        {!history.length && <p className="text-sm text-muted">No completed, rejected or cancelled transfers yet.</p>}
        {history.length > 0 && !shown.length && <p className="text-sm text-muted">No transfers with this status.</p>}
        <ul className="space-y-4" aria-label="My transfer history">
          {shown.map((request) => (
            <li key={request.transfer_request_id} className="ui-panel space-y-3 p-4 sm:p-5">
              <p className="text-xs text-muted">
                {request.initiated_by && request.initiated_by !== 'student' ? 'Transferred' : 'Submitted'}{' '}
                {formatTransferDate(request.submitted_at)}
              </p>
              <TransferSummary request={request} />
              {request.status === 'approved' && request.previous_enrollments.length > 0 && (
                <p className="text-sm text-content">
                  Subjects from your previous section were released. Open Semester Registration to choose your subjects
                  in the new section.
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

import type { TransferRequest } from '../../../types/transfer.ts'
import TransferSummary from '../../transfers/TransferSummary.tsx'
import { formatTransferDate, isOpenTransfer } from '../../transfers/transferLabels.ts'

/** The student's transfer requests, newest first, each with its own history. */
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
  if (!requests.length) return <p className="text-sm text-muted">You have not requested a transfer yet.</p>
  return (
    <ul className="space-y-4" aria-label="My transfer requests">
      {requests.map((request) => (
        <li key={request.transfer_request_id} className="ui-panel space-y-3 p-4 sm:p-5">
          <p className="text-xs text-muted">Submitted {formatTransferDate(request.submitted_at)}</p>
          <TransferSummary request={request} />
          {request.status === 'approved' && request.previous_enrollments.length > 0 && (
            <p className="text-sm text-content">
              Subjects from your previous section were released. Open Semester Registration to choose your subjects in
              the new section.
            </p>
          )}
          {canCancel && isOpenTransfer(request.status) && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onCancel(request.transfer_request_id)}
              className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover disabled:opacity-50"
            >
              Cancel request
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}

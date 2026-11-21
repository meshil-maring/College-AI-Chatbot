import { useId, useState } from 'react'
import type { TransferDecisionAction, TransferRequest } from '../../../types/transfer.ts'
import TransferSummary from '../TransferSummary.tsx'
import { formatTransferDate, isOpenTransfer, seatSummary } from '../transferLabels.ts'

type Pending = Exclude<TransferDecisionAction, 'start_review'> | null

export default function TransferReviewCard({
  request,
  canDecide,
  busy,
  onDecide,
}: {
  request: TransferRequest
  canDecide: boolean
  busy: boolean
  onDecide: (action: TransferDecisionAction, comment: string | null) => void
}) {
  const id = useId()
  const [pending, setPending] = useState<Pending>(null)
  const [comment, setComment] = useState('')
  const trimmed = comment.trim()
  const open = isOpenTransfer(request.status)
  const target = request.to_section
  const full = target !== null && target.capacity !== null && target.seats_taken >= target.capacity
  const confirm = () => {
    if (!pending || (pending === 'reject' && !trimmed)) return
    onDecide(pending, trimmed || null)
  }
  return (
    <li className="ui-panel space-y-3 p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-semibold text-content">
          {request.student_name ?? 'Student'}
          {request.register_number ? <span className="text-muted"> · {request.register_number}</span> : null}
        </h3>
        <span className="text-xs text-muted">Submitted {formatTransferDate(request.submitted_at)}</span>
      </div>
      <TransferSummary request={request} />
      {open && target && (
        <p className={`text-sm ${full ? 'text-danger' : 'text-muted'}`}>
          Target section: {full ? 'full — approval will fail until a seat is free' : seatSummary(target)}
        </p>
      )}
      {open && canDecide && pending === null && (
        <div className="flex flex-wrap gap-2">
          {request.status === 'submitted' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onDecide('start_review', null)}
              className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover disabled:opacity-50"
            >
              Start review
            </button>
          )}
          <button
            type="button"
            disabled={busy || full}
            onClick={() => setPending('approve')}
            className="min-h-11 rounded-lg bg-accent px-4 py-2 font-medium text-ink hover:bg-accent-hover disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setPending('reject')}
            className="min-h-11 rounded-lg border border-control px-4 py-2 text-danger hover:bg-hover disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      )}
      {open && pending && (
        <div className="space-y-2 rounded-lg border border-line p-3">
          <label htmlFor={`${id}-comment`} className="block text-sm font-semibold text-content">
            {pending === 'reject' ? 'Reason for rejection (shown to the student)' : 'Note to the student (optional)'}
          </label>
          <textarea
            id={`${id}-comment`}
            rows={3}
            maxLength={2000}
            value={comment}
            disabled={busy}
            onChange={(event) => setComment(event.target.value)}
            className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-content"
          />
          {pending === 'approve' && (
            <p className="text-xs text-muted">
              Approving moves the student into the new section now. Their subject registration for this term is cleared
              and they must register again.
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => setPending(null)}
              className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover"
            >
              Back
            </button>
            <button
              type="button"
              disabled={busy || (pending === 'reject' && !trimmed)}
              onClick={confirm}
              className="min-h-11 rounded-lg bg-accent px-4 py-2 font-medium text-ink hover:bg-accent-hover disabled:opacity-50"
            >
              {pending === 'reject' ? 'Confirm rejection' : 'Confirm approval'}
            </button>
          </div>
        </div>
      )}
    </li>
  )
}

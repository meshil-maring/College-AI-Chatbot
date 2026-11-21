import { ArrowRight } from 'lucide-react'
import type { TransferRequest } from '../../types/transfer.ts'
import {
  TRANSFER_EVENT_LABEL,
  TRANSFER_INITIATOR_LABEL,
  TRANSFER_STATUS_LABEL,
  TRANSFER_STATUS_TONE,
  TRANSFER_TYPE_LABEL,
  describeSection,
  formatTransferDate,
} from './transferLabels.ts'

export function TransferStatusBadge({ status }: { status: TransferRequest['status'] }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${TRANSFER_STATUS_TONE[status]}`}>
      {TRANSFER_STATUS_LABEL[status]}
    </span>
  )
}

/** Placement change, reason, decision and history shared by students and reviewers. */
export default function TransferSummary({ request }: { request: TransferRequest }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">
          {TRANSFER_TYPE_LABEL[request.transfer_type]}
          {request.initiated_by && request.initiated_by !== 'student'
            ? ` · ${TRANSFER_INITIATOR_LABEL[request.initiated_by]}`
            : ''}
        </span>
        <TransferStatusBadge status={request.status} />
      </div>
      <div className="flex flex-col gap-2 text-sm text-content sm:flex-row sm:items-center">
        <span>{describeSection(request.from_section)}</span>
        <ArrowRight size={16} aria-label="to" className="shrink-0 text-muted" />
        <span className="font-medium">{describeSection(request.to_section)}</span>
      </div>
      <p className="text-sm text-content">
        <span className="font-medium">Reason: </span>
        {request.reason}
      </p>
      {request.decision_comment && (
        <p className={`text-sm ${request.status === 'rejected' ? 'text-danger' : 'text-content'}`}>
          <span className="font-medium">
            {request.status === 'rejected' ? 'Rejection reason' : 'Reviewer note'}
            {request.decided_as ? ` (${request.decided_as === 'hod' ? 'HOD' : 'Administrator'})` : ''}:{' '}
          </span>
          {request.decision_comment}
        </p>
      )}
      <ol className="space-y-1 border-l border-line pl-4" aria-label="Request history">
        {request.events.map((event, index) => (
          <li key={`${event.action}-${event.created_at}-${index}`} className="text-xs text-muted">
            <span className="font-medium text-content">{TRANSFER_EVENT_LABEL[event.action]}</span>
            {' · '}
            {formatTransferDate(event.created_at)}
            {event.comment && event.action !== 'rejected' ? ` — ${event.comment}` : ''}
          </li>
        ))}
      </ol>
    </div>
  )
}

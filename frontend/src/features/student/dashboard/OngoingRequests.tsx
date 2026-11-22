/** Open section/program transfer requests, linking to Transfer Requests. */

import { ArrowLeftRight } from 'lucide-react'
import type { TransferRequest } from '../../../types/transfer.ts'
import { TRANSFER_STATUS_LABEL, TRANSFER_STATUS_TONE, TRANSFER_TYPE_LABEL } from '../../transfers/transferLabels.ts'
import { EmptyBlock } from '../shared/SectionState.tsx'
import { DashboardPanel, ReadState, ViewAllButton } from './DashboardPanel.tsx'
import type { DashboardRead } from './useDashboardData.ts'

function RequestRow({ request }: { request: TransferRequest }) {
  const from = request.from_section?.section_name ?? '—'
  const to = request.to_section?.section_name ?? '—'
  return (
    <li className="flex min-w-0 flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-warning-bg text-accent">
        <ArrowLeftRight aria-hidden="true" className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-content">{TRANSFER_TYPE_LABEL[request.transfer_type]}</p>
        <p className="truncate text-sm text-muted">
          {from} <span aria-label="to">→</span> <span className="text-accent">{to}</span>
        </p>
      </div>
      <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${TRANSFER_STATUS_TONE[request.status]}`}>
        {TRANSFER_STATUS_LABEL[request.status]}
      </span>
    </li>
  )
}

export default function OngoingRequests({
  requests,
  onViewAll,
}: {
  requests: DashboardRead<TransferRequest[]>
  onViewAll: () => void
}) {
  return (
    <DashboardPanel
      icon={ArrowLeftRight}
      title="Ongoing Requests"
      headingId="dashboard-requests"
      action={requests.status === 'unavailable' ? undefined : <ViewAllButton onClick={onViewAll} />}
    >
      <ReadState
        read={requests}
        loadingLabel="Loading requests…"
        errorMessage="Unable to load your requests."
        unavailableMessage="Requests are unavailable for this account."
      >
        {(items) =>
          !items || items.length === 0 ? (
            <EmptyBlock message="No ongoing requests." />
          ) : (
            <ul className="divide-y divide-line">
              {items.map((request) => (
                <RequestRow key={request.transfer_request_id} request={request} />
              ))}
            </ul>
          )
        }
      </ReadState>
    </DashboardPanel>
  )
}

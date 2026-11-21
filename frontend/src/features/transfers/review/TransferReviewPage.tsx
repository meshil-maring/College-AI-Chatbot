import { useMemo, useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import type { TransferStatus } from '../../../types/transfer.ts'
import TransferReviewCard from './TransferReviewCard.tsx'
import TransferReviewTabs from './TransferReviewTabs.tsx'
import TransferReviewToolbar from './TransferReviewToolbar.tsx'
import {
  EMPTY_FILTERS,
  filterFacets,
  filterTransfers,
  hasActiveFilters,
  statusCounts,
  tabFor,
  type ReviewTab,
  type TransferFilters,
} from './transferFilters.ts'
import { useTransferReviews } from './useTransferReviews.ts'

const PAGE_SIZE = 20

/** Transfer review queue and history for institution administrators and Heads of Department. */
export default function TransferReviewPage() {
  const { accessToken, user, role, sessionGeneration } = useAuth()
  if (!accessToken || !user?.institution_id || (role !== 'admin' && role !== 'faculty'))
    return <p role="status">Transfer reviews are unavailable for this account.</p>
  const identity = transferReviewIdentity(sessionGeneration, user.user_id, user.institution_id, role)
  return <ReviewSession key={identity} identity={identity} institutionId={user.institution_id} token={accessToken} />
}

export function transferReviewIdentity(
  generation: number | null | undefined,
  userId: string,
  institutionId: string,
  role: string | null,
) {
  return JSON.stringify([generation ?? 0, userId, institutionId, role])
}

function ReviewSession({ identity, institutionId, token }: { identity: string; institutionId: string; token: string }) {
  const [tab, setTab] = useState<ReviewTab>('pending')
  const [filters, setFilters] = useState<TransferFilters>(EMPTY_FILTERS)
  const [visible, setVisible] = useState(PAGE_SIZE)
  const [notice, setNotice] = useState<string | null>(null)
  // One read of every request in scope; search and filters run on it locally.
  const { query, decide } = useTransferReviews(identity, institutionId, token, 'all')
  const data = query.data
  const requests = useMemo(() => data?.requests ?? [], [data])
  const counts = useMemo(() => statusCounts(requests), [requests])
  const facets = useMemo(() => filterFacets(requests), [requests])
  const results = useMemo(() => filterTransfers(requests, tab, filters), [requests, tab, filters])
  const change = (next: Partial<TransferFilters>) => {
    setFilters((current) => ({ ...current, ...next }))
    setVisible(PAGE_SIZE)
  }
  const switchTab = (next: ReviewTab) => {
    setTab(next)
    change({ status: 'all' })
  }
  const pickStatus = (status: TransferStatus) => {
    setTab(tabFor(status))
    change({ status: filters.status === status ? 'all' : status })
  }
  return (
    <section className="space-y-5" aria-label="Transfer reviews">
      {data?.can_review && (
        <p className="text-muted">
          {data.reviewer_role === 'admin'
            ? 'Review every transfer request in this institution and browse the full transfer history.'
            : `You review transfers into ${data.departments.map((item) => item.name).join(', ')} as Head of Department.`}
        </p>
      )}
      {query.isPending && (
        <div role="status" aria-label="Loading transfer requests" className="space-y-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="ui-panel h-24 animate-pulse motion-reduce:animate-none" />
          ))}
        </div>
      )}
      {query.error instanceof Error && (
        <div role="alert" className="ui-panel flex flex-wrap items-center justify-between gap-3 p-4">
          <p>{query.error.message}</p>
          <button
            type="button"
            onClick={() => void query.refetch()}
            className="min-h-10 rounded-lg border border-control px-4 hover:bg-hover"
          >
            Retry
          </button>
        </div>
      )}
      {decide.error instanceof Error && (
        <div role="alert" className="ui-panel p-4">
          <p>{decide.error.message}</p>
        </div>
      )}
      {notice && (
        <p role="status" className="rounded-lg bg-success-bg px-4 py-3 text-success">
          {notice}
        </p>
      )}
      {data && !data.can_review && (
        <p role="status">
          You are not an administrator or a current Head of Department, so no transfers are assigned to you.
        </p>
      )}
      {data?.can_review && (
        <>
          <TransferReviewTabs
            tab={tab}
            activeStatus={filters.status}
            counts={counts}
            onTab={switchTab}
            onStatus={pickStatus}
          />
          <TransferReviewToolbar
            tab={tab}
            filters={filters}
            programs={facets.programs}
            departments={facets.departments}
            showDepartments={data.reviewer_role === 'admin' && facets.departments.length > 1}
            resultCount={results.length}
            onChange={change}
            onClear={() => change({ ...EMPTY_FILTERS, sort: filters.sort })}
          />
          {!results.length ? (
            <div className="ui-panel space-y-2 p-8 text-center" role="status">
              <p className="font-medium text-content">
                {hasActiveFilters(filters)
                  ? 'No transfer requests match these filters.'
                  : tab === 'pending'
                    ? 'No transfer requests are waiting for a decision.'
                    : 'No completed transfers yet.'}
              </p>
              {hasActiveFilters(filters) && (
                <button
                  type="button"
                  onClick={() => change({ ...EMPTY_FILTERS, sort: filters.sort })}
                  className="min-h-10 rounded-lg border border-control px-4 hover:bg-hover"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <ul className="space-y-4" aria-label={tab === 'pending' ? 'Pending transfer requests' : 'Transfer history'}>
              {results.slice(0, visible).map((request) => (
                <TransferReviewCard
                  key={request.transfer_request_id}
                  request={request}
                  canDecide={data.can_decide}
                  busy={decide.isPending}
                  onDecide={(action, comment) =>
                    decide.mutate(
                      { requestId: request.transfer_request_id, action, comment },
                      {
                        onSuccess: (result) =>
                          setNotice(
                            result.status === 'approved'
                              ? `${request.student_name ?? 'The student'} was moved to the new section.`
                              : result.status === 'rejected'
                                ? 'Transfer rejected. The student can see your reason.'
                                : 'Marked as under review.',
                          ),
                      },
                    )
                  }
                />
              ))}
            </ul>
          )}
          {results.length > visible && (
            <button
              type="button"
              onClick={() => setVisible((count) => count + PAGE_SIZE)}
              className="min-h-11 w-full rounded-lg border border-control px-4 hover:bg-hover"
            >
              Show more ({results.length - visible} remaining)
            </button>
          )}
        </>
      )}
    </section>
  )
}

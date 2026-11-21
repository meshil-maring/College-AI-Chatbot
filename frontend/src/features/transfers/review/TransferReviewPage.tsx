import { useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import TransferReviewCard from './TransferReviewCard.tsx'
import { useTransferReviews, type ReviewFilter } from './useTransferReviews.ts'

/** Transfer review queue for institution administrators and Heads of Department. */
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
  const [filter, setFilter] = useState<ReviewFilter>('open')
  const [notice, setNotice] = useState<string | null>(null)
  const { query, decide } = useTransferReviews(identity, institutionId, token, filter)
  const data = query.data
  const error = query.error ?? decide.error
  return (
    <section className="space-y-5" aria-label="Transfer reviews">
      {data?.can_review && (
        <p className="text-muted">
          {data.reviewer_role === 'admin'
            ? 'You can review every transfer request in this institution.'
            : `You review transfers into ${data.departments.map((item) => item.name).join(', ')} as Head of Department.`}
        </p>
      )}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter requests">
        {(['open', 'all'] as const).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
            className={`min-h-11 rounded-lg border px-4 py-2 ${
              filter === value ? 'border-accent bg-accent text-ink' : 'border-control hover:bg-hover'
            }`}
          >
            {value === 'open' ? 'Awaiting decision' : 'All requests'}
          </button>
        ))}
      </div>
      {query.isPending && <p role="status">Loading transfer requests…</p>}
      {error instanceof Error && (
        <div role="alert" className="ui-panel p-4">
          <p>{error.message}</p>
        </div>
      )}
      {notice && <p role="status">{notice}</p>}
      {data && !data.can_review && (
        <p role="status">
          You are not an administrator or a current Head of Department, so no transfers are assigned to you.
        </p>
      )}
      {data?.can_review && !data.requests.length && (
        <p role="status">{filter === 'open' ? 'No transfer requests are waiting.' : 'No transfer requests yet.'}</p>
      )}
      {data?.can_review && data.requests.length > 0 && (
        <ul className="space-y-4" aria-label="Transfer requests">
          {data.requests.map((request) => (
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
                          ? 'Transfer approved. The student has been moved to the new section.'
                          : result.status === 'rejected'
                            ? 'Transfer rejected.'
                            : 'Marked as under review.',
                      ),
                  },
                )
              }
            />
          ))}
        </ul>
      )}
    </section>
  )
}

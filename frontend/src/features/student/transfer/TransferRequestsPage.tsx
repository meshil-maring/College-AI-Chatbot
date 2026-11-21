import { useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { hasPermission } from '../../auth/access/permissions.ts'
import type { StudentTransfers } from '../../../types/transfer.ts'
import { describeSection, formatTransferDate, isOpenTransfer } from '../../transfers/transferLabels.ts'
import TransferForm from './TransferForm.tsx'
import TransferTimeline from './TransferTimeline.tsx'
import { useStudentTransfers } from './useStudentTransfers.ts'

export default function TransferRequestsPage() {
  const { accessToken, user, role, sessionGeneration } = useAuth()
  const permissions = user?.effective_permissions
  if (!accessToken || !user?.institution_id || role !== 'student' || !hasPermission(permissions, 'transfers.read'))
    return <p role="status">Transfer requests are unavailable for this account.</p>
  const identity = JSON.stringify([
    sessionGeneration ?? 0,
    user.user_id,
    user.institution_id,
    role,
    [...(permissions ?? [])].sort(),
  ])
  return (
    <TransferSession
      key={identity}
      identity={identity}
      institutionId={user.institution_id}
      token={accessToken}
      canRequest={hasPermission(permissions, 'transfers.request')}
    />
  )
}

function TransferSession({
  identity,
  institutionId,
  token,
  canRequest,
}: {
  identity: string
  institutionId: string
  token: string
  canRequest: boolean
}) {
  const { query, submit, cancel } = useStudentTransfers(identity, institutionId, token)
  const [showForm, setShowForm] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const busy = submit.isPending || cancel.isPending
  const error = query.error ?? submit.error ?? cancel.error
  const data = query.data
  return (
    <section className="space-y-5" aria-label="Transfer Requests">
      <p className="text-muted">
        Ask to move to another section of your batch, or to a section of another program. Your Head of Department or an
        administrator reviews each request.
      </p>
      {query.isPending && <p role="status">Loading your placement…</p>}
      {error instanceof Error && (
        <div role="alert" className="ui-panel p-4">
          <p>{error.message}</p>
        </div>
      )}
      {notice && <p role="status">{notice}</p>}
      {data && (
        <>
          <CurrentPlacement data={data} />
          {showForm ? (
            <TransferForm
              options={data.options}
              registered={data.current?.registration_status === 'registered'}
              busy={busy}
              onCancel={() => setShowForm(false)}
              onSubmit={(body) =>
                submit.mutate(body, {
                  onSuccess: () => {
                    setShowForm(false)
                    setNotice('Your transfer request was submitted.')
                  },
                })
              }
            />
          ) : (
            <RequestAction data={data} canRequest={canRequest} onStart={() => setShowForm(true)} />
          )}
          <TransferTimeline
            requests={data.requests}
            canCancel={canRequest}
            busy={busy}
            onCancel={(requestId) =>
              cancel.mutate(requestId, { onSuccess: () => setNotice('Your transfer request was cancelled.') })
            }
          />
        </>
      )}
    </section>
  )
}

function CurrentPlacement({ data }: { data: StudentTransfers }) {
  if (!data.current)
    return (
      <p role="status" className="ui-panel p-4">
        You are not assigned to a section yet. Contact your administrator before requesting a transfer.
      </p>
    )
  return (
    <div className="ui-panel p-4 sm:p-5">
      <h2 className="text-section font-semibold text-content">Current placement</h2>
      <p className="text-content">{describeSection(data.current)}</p>
      <p className="text-sm text-muted">
        {data.current.department_name} · {data.current.term_name} (ends {formatTransferDate(data.current.term_end_date)}
        )
      </p>
    </div>
  )
}

function RequestAction({
  data,
  canRequest,
  onStart,
}: {
  data: StudentTransfers
  canRequest: boolean
  onStart: () => void
}) {
  if (!canRequest || !data.current) return null
  if (data.requests.some((request) => isOpenTransfer(request.status)))
    return <p className="text-sm text-muted">You have an open request. Cancel it to request a different section.</p>
  if (!data.current.term_open)
    return <p className="text-sm text-muted">Transfers are closed because your current term has ended.</p>
  if (!data.options.length)
    return <p className="text-sm text-muted">No other sections are open for transfer in your current term.</p>
  return (
    <button
      type="button"
      onClick={onStart}
      className="min-h-11 rounded-lg bg-accent px-4 py-2 font-medium text-ink hover:bg-accent-hover"
    >
      Request a transfer
    </button>
  )
}

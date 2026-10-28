import { useStaffFacultyManagement } from './useStaffFacultyManagement.ts'

export default function StaffFacultyManager({ accessToken }: { accessToken: string }) {
  const { requestFilter, setRequestFilter, requests, members, loading, actionKey, error, success, decide, lifecycle } =
    useStaffFacultyManagement(accessToken)

  const buttonClass =
    'rounded-lg border border-control px-3 py-2 text-xs font-medium hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50'

  return (
    <div className="space-y-8">
      {error ? (
        <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
          {error}
        </p>
      ) : null}
      {success ? (
        <p role="status" className="rounded-lg border border-success bg-success-bg p-3 text-sm text-success">
          {success}
        </p>
      ) : null}

      <section aria-labelledby="membership-requests-heading" className="rounded-xl border border-line bg-surface p-4">
        <h2 id="membership-requests-heading" className="font-semibold text-content text-section">
          Requests
        </h2>
        <p className="mt-2 text-sm text-muted">
          If an approved account cannot sign in, choose All, Staff or Faculty and retry its sign-in setup.
        </p>
        <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Request filters">
          {(['all', 'staff', 'faculty', 'pending'] as const).map((filter) => (
            <button
              key={filter}
              type="button"
              role="tab"
              aria-selected={requestFilter === filter}
              onClick={() => setRequestFilter(filter)}
              className={`${buttonClass} ${requestFilter === filter ? 'bg-accent text-ink' : 'text-content'}`}
            >
              {filter[0].toUpperCase() + filter.slice(1)}
            </button>
          ))}
        </div>
        {loading ? (
          <p role="status" className="mt-4 text-sm text-muted">
            Loading membership requests…
          </p>
        ) : requests.length === 0 ? (
          <p className="mt-4 text-sm text-muted">No membership requests match this filter.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {requests.map((request) => (
              <article
                key={request.request_id}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-3"
              >
                <div className="mr-auto min-w-0">
                  <p className="font-medium text-content">{request.full_name || 'Unnamed applicant'}</p>
                  <p className="break-all text-sm text-muted">{request.email}</p>
                  <p className="text-xs capitalize text-muted">
                    {request.requested_role} · {request.status}
                  </p>
                </div>
                {request.status === 'pending' ? (
                  <>
                    <button
                      type="button"
                      disabled={actionKey !== null}
                      onClick={() => void decide(request, 'approve')}
                      className={`${buttonClass} text-success`}
                    >
                      {actionKey === `approve:${request.request_id}` ? 'Approving…' : 'Approve'}
                    </button>
                    <button
                      type="button"
                      disabled={actionKey !== null}
                      onClick={() => void decide(request, 'reject')}
                      className={`${buttonClass} text-danger`}
                    >
                      {actionKey === `reject:${request.request_id}` ? 'Rejecting…' : 'Reject'}
                    </button>
                  </>
                ) : request.status === 'approved' ? (
                  <button
                    type="button"
                    disabled={actionKey !== null}
                    onClick={() => void decide(request, 'approve')}
                    className={buttonClass}
                  >
                    {actionKey === `approve:${request.request_id}` ? 'Retrying…' : 'Retry sign-in setup'}
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="membership-roster-heading" className="rounded-xl border border-line bg-surface p-4">
        <h2 id="membership-roster-heading" className="font-semibold text-content text-section">
          Roster
        </h2>
        {loading ? (
          <p role="status" className="mt-4 text-sm text-muted">
            Loading roster…
          </p>
        ) : members.length === 0 ? (
          <p className="mt-4 text-sm text-muted">No staff or faculty are on the roster yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead className="text-xs uppercase text-muted">
                <tr>
                  <th className="p-2">Name</th>
                  <th className="p-2">Email</th>
                  <th className="p-2">Role</th>
                  <th className="p-2">Status</th>
                  <th className="p-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.user_id} className="border-t border-line">
                    <td className="p-2 text-content">{member.name || 'Pending setup'}</td>
                    <td className="p-2 text-muted">{member.email}</td>
                    <td className="p-2 capitalize text-muted">{member.role}</td>
                    <td className="p-2 capitalize text-muted">{member.status}</td>
                    <td className="p-2">
                      {member.user_id && member.status === 'active' ? (
                        <button
                          type="button"
                          disabled={actionKey !== null}
                          onClick={() => void lifecycle(member, 'deactivate')}
                          className={buttonClass}
                        >
                          {actionKey === `deactivate:${member.user_id}` ? 'Deactivating…' : 'Deactivate'}
                        </button>
                      ) : null}
                      {member.user_id && (member.status === 'inactive' || member.status === 'deactivated') ? (
                        <button
                          type="button"
                          disabled={actionKey !== null}
                          onClick={() => void lifecycle(member, 'reactivate')}
                          className={buttonClass}
                        >
                          {actionKey === `reactivate:${member.user_id}` ? 'Reactivating…' : 'Reactivate'}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

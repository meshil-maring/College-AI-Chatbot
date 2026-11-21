import { useState } from 'react'
import type { Department } from '../../../types/academicSetup.ts'
import type { MembershipRequest, MembershipRole } from '../../../types/admin.ts'

type RequestFilter = 'all' | MembershipRole | 'pending'

export const BUTTON_CLASS =
  'rounded-lg border border-control px-3 py-2 text-xs font-medium hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50'
export const SELECT_CLASS =
  'rounded-lg border border-control bg-surface px-2 py-2 text-xs text-content focus:border-accent focus:outline-none disabled:opacity-50'

interface Props {
  requestFilter: RequestFilter
  setRequestFilter: (filter: RequestFilter) => void
  requests: MembershipRequest[]
  departments: Department[]
  loading: boolean
  actionKey: string | null
  decide: (
    request: MembershipRequest,
    decision: 'approve' | 'reject',
    departmentId?: string,
    role?: MembershipRole,
  ) => Promise<void>
}

export const ROLE_OPTIONS: readonly { value: MembershipRole; label: string }[] = [
  { value: 'faculty', label: 'Faculty' },
  { value: 'staff', label: 'Staff' },
]

/**
 * Staff and Faculty sign-up requests. Applicants do not choose a department:
 * the administrator picks one for each pending request before approving it,
 * and confirms whether the person joins as Staff or Faculty.
 */
export default function MembershipRequests({
  requestFilter,
  setRequestFilter,
  requests,
  departments,
  loading,
  actionKey,
  decide,
}: Props) {
  const [chosen, setChosen] = useState<Record<string, string>>({})
  const [roles, setRoles] = useState<Record<string, MembershipRole>>({})

  return (
    <section aria-labelledby="membership-requests-heading" className="rounded-xl border border-line bg-surface p-4">
      <h2 id="membership-requests-heading" className="font-semibold text-content text-section">
        Requests
      </h2>
      <p className="mt-2 text-sm text-muted">
        Choose the role and department for each new Staff or Faculty member, then approve. If an approved account cannot
        sign in, choose All, Staff or Faculty and retry its sign-in setup.
      </p>
      <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Request filters">
        {(['all', 'staff', 'faculty', 'pending'] as const).map((filter) => (
          <button
            key={filter}
            type="button"
            role="tab"
            aria-selected={requestFilter === filter}
            onClick={() => setRequestFilter(filter)}
            className={`${BUTTON_CLASS} ${requestFilter === filter ? 'bg-accent text-ink' : 'text-content'}`}
          >
            {filter[0].toUpperCase() + filter.slice(1)}
          </button>
        ))}
      </div>
      {!loading && departments.length === 0 ? (
        <p className="mt-3 text-sm text-warning">
          No active departments yet. Add one in Academic Setup before approving requests.
        </p>
      ) : null}
      {loading ? (
        <p role="status" className="mt-4 text-sm text-muted">
          Loading membership requests…
        </p>
      ) : requests.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No membership requests match this filter.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {requests.map((request) => {
            const departmentId = chosen[request.request_id] ?? ''
            // Starts at the role the applicant asked for; the administrator decides.
            const role = roles[request.request_id] ?? request.requested_role
            const label = request.full_name || request.email
            return (
              <article
                key={request.request_id}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-3"
              >
                <div className="mr-auto min-w-0">
                  <p className="font-medium text-content">{request.full_name || 'Unnamed applicant'}</p>
                  <p className="break-all text-sm text-muted">{request.email}</p>
                  <p className="text-xs capitalize text-muted">
                    Asked for {request.requested_role} · {request.status}
                  </p>
                </div>
                {request.status === 'pending' ? (
                  <>
                    <select
                      aria-label={`Role for ${label}`}
                      value={role}
                      disabled={actionKey !== null}
                      onChange={(event) =>
                        setRoles((previous) => ({
                          ...previous,
                          [request.request_id]: event.target.value as MembershipRole,
                        }))
                      }
                      className={SELECT_CLASS}
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <select
                      aria-label={`Department for ${label}`}
                      value={departmentId}
                      disabled={actionKey !== null || departments.length === 0}
                      onChange={(event) =>
                        setChosen((previous) => ({ ...previous, [request.request_id]: event.target.value }))
                      }
                      className={SELECT_CLASS}
                    >
                      <option value="">Choose department…</option>
                      {departments.map((department) => (
                        <option key={department.department_id} value={department.department_id}>
                          {department.name} ({department.code})
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={actionKey !== null || departmentId === ''}
                      title={departmentId === '' ? 'Choose a department first' : undefined}
                      onClick={() => void decide(request, 'approve', departmentId, role)}
                      className={`${BUTTON_CLASS} text-success`}
                    >
                      {actionKey === `approve:${request.request_id}` ? 'Approving…' : 'Approve'}
                    </button>
                    <button
                      type="button"
                      disabled={actionKey !== null}
                      onClick={() => void decide(request, 'reject')}
                      className={`${BUTTON_CLASS} text-danger`}
                    >
                      {actionKey === `reject:${request.request_id}` ? 'Rejecting…' : 'Reject'}
                    </button>
                  </>
                ) : request.status === 'approved' ? (
                  <button
                    type="button"
                    disabled={actionKey !== null}
                    onClick={() => void decide(request, 'approve')}
                    className={BUTTON_CLASS}
                  >
                    {actionKey === `approve:${request.request_id}` ? 'Retrying…' : 'Retry sign-in setup'}
                  </button>
                ) : null}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

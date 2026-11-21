import { Inbox } from 'lucide-react'
import { useState } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRequest, MembershipRole } from '../../../../types/admin.ts'
import type { RequestFilter } from '../staffFacultyKeys.ts'
import MembershipRequestCard from './MembershipRequestCard.tsx'

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

const FILTERS: readonly { value: RequestFilter; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'all', label: 'All' },
  { value: 'staff', label: 'Staff' },
  { value: 'faculty', label: 'Faculty' },
]

const EMPTY_TEXT: Record<RequestFilter, string> = {
  pending: 'You are all caught up. New Staff and Faculty sign-ups will appear here.',
  all: 'No membership requests match this filter.',
  staff: 'No membership requests match this filter.',
  faculty: 'No membership requests match this filter.',
}

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
    <section
      aria-labelledby="membership-requests-heading"
      className="space-y-4 rounded-xl border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="membership-requests-heading" className="sr-only">
            Requests
          </h2>
          <p className="mt-1 max-w-[70ch] text-sm text-muted">
            Choose the role and department for each new Staff or Faculty member, then approve. If an approved account
            cannot sign in, open All, Staff or Faculty and retry its sign-in setup.
          </p>
        </div>
        <div
          className="flex flex-wrap gap-1 rounded-lg border border-line bg-canvas p-1"
          role="tablist"
          aria-label="Request filters"
        >
          {FILTERS.map((filter) => {
            const selected = requestFilter === filter.value
            return (
              <button
                key={filter.value}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setRequestFilter(filter.value)}
                className={`min-h-9 rounded-md px-3 text-sm font-semibold ${
                  selected ? 'bg-accent text-ink' : 'text-muted hover:bg-hover hover:text-content'
                }`}
              >
                {filter.label}
              </button>
            )
          })}
        </div>
      </div>

      {!loading && departments.length === 0 ? (
        <p className="rounded-lg border border-warning bg-warning-bg p-3 text-sm text-warning">
          No active departments yet. Add one in Academic Setup before approving requests.
        </p>
      ) : null}

      {loading ? (
        <p role="status" className="text-sm text-muted">
          Loading membership requests…
        </p>
      ) : requests.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Inbox aria-hidden="true" className="size-8 text-muted" />
          <p className="text-sm text-muted">{EMPTY_TEXT[requestFilter]}</p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-muted">
            {requests.length} {requests.length === 1 ? 'request' : 'requests'}
          </p>
          {requests.map((request) => (
            <MembershipRequestCard
              key={request.request_id}
              request={request}
              departments={departments}
              // Starts at the role the applicant asked for; the administrator decides.
              role={roles[request.request_id] ?? request.requested_role}
              departmentId={chosen[request.request_id] ?? ''}
              onRoleChange={(role) => setRoles((previous) => ({ ...previous, [request.request_id]: role }))}
              onDepartmentChange={(id) => setChosen((previous) => ({ ...previous, [request.request_id]: id }))}
              actionKey={actionKey}
              decide={decide}
            />
          ))}
        </div>
      )}
    </section>
  )
}

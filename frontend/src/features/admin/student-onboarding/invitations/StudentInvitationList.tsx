import { RefreshCw, Search } from 'lucide-react'
import { useState } from 'react'
import type { StudentInvitation } from '../../../../types/admin/students.ts'
import type { PlacementOptions } from '../placement/usePlacementOptions.ts'
import InvitationMetrics from './InvitationMetrics.tsx'
import InvitationRow from './InvitationRow.tsx'
import { countInvitations, filterInvitations, type InvitationFilter } from './invitationFilters.ts'

export default function StudentInvitationList({
  invitations,
  placement,
  loading,
  error,
  fetching,
  busy,
  onRefresh,
  onResend,
  onReassign,
}: {
  invitations: StudentInvitation[]
  placement: Pick<PlacementOptions, 'cohorts' | 'sections'>
  loading: boolean
  error: string
  fetching: boolean
  busy: boolean
  onRefresh: () => void
  onResend: (invitationId: string) => void
  onReassign: (invitationId: string, sectionId: string) => Promise<boolean>
}) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<InvitationFilter>('all')
  const visible = filterInvitations(invitations, search, filter)
  const narrowed = Boolean(search.trim()) || filter !== 'all'

  return (
    <section className="student-onboarding-records" aria-labelledby="pending-student-invitations-heading">
      <InvitationMetrics
        counts={countInvitations(invitations)}
        unavailable={loading || Boolean(error)}
        filter={filter}
        onFilter={setFilter}
      />
      <div className="student-invitation-section">
        <header className="student-invitation-heading">
          <div>
            <h2 id="pending-student-invitations-heading">Pending invitations</h2>
            <p>Students who have not finished account setup. Resend a link or move them to another section.</p>
          </div>
          <button type="button" disabled={fetching} onClick={onRefresh}>
            <RefreshCw size={15} aria-hidden="true" />
            {fetching ? 'Refreshing…' : 'Refresh'}
          </button>
        </header>
        {invitations.length > 0 && (
          <div className="student-invitation-toolbar">
            <label className="student-invitation-search">
              <Search size={15} aria-hidden="true" />
              <span className="sr-only">Search pending invitations</span>
              <input
                type="search"
                value={search}
                placeholder="Search name, email, register number or section"
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <span role="status" className="student-invitation-count">
              {narrowed ? `${visible.length} of ${invitations.length} shown` : `${invitations.length} total`}
            </span>
          </div>
        )}
        {loading && <p role="status">Loading invitations…</p>}
        {error && <p role="alert">{error}</p>}
        {!loading && !error && !invitations.length && <p role="status">No pending student invitations.</p>}
        {invitations.length > 0 && !visible.length && (
          <p className="student-invitation-empty">
            No invitations match.{' '}
            <button
              type="button"
              className="student-onboarding-text-button"
              onClick={() => {
                setSearch('')
                setFilter('all')
              }}
            >
              Clear search and filter
            </button>
          </p>
        )}
        {!loading && !error && visible.length > 0 && (
          <div className="student-invitation-table-scroll">
            <table className="student-invitation-table">
              <caption className="sr-only">Pending student setup invitations</caption>
              <thead>
                <tr>
                  <th scope="col">Student</th>
                  <th scope="col">Register No.</th>
                  <th scope="col">Batch / Section</th>
                  <th scope="col">Email status</th>
                  <th scope="col">Link expires</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((invite) => (
                  <InvitationRow
                    key={invite.invitation_id}
                    invite={invite}
                    placement={placement}
                    busy={busy}
                    onResend={onResend}
                    onReassign={onReassign}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}

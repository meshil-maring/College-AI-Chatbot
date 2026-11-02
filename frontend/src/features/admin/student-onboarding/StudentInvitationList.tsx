import { RefreshCw } from 'lucide-react'
import type { StudentInvitation } from '../../../types/admin/students.ts'

export default function StudentInvitationList({
  invitations,
  loading,
  error,
  fetching,
  busy,
  sectionId,
  onRefresh,
  onResend,
  onReassign,
}: {
  invitations: StudentInvitation[]
  loading: boolean
  error: string
  fetching: boolean
  busy: boolean
  sectionId: string
  onRefresh: () => void
  onResend: (invitationId: string) => void
  onReassign: (invitationId: string) => void
}) {
  return (
    <section className="student-invitation-section" aria-labelledby="pending-student-invitations-heading">
      <header className="student-invitation-heading">
        <div>
          <h2 id="pending-student-invitations-heading">Pending invitations</h2>
          <p>Track setup-link delivery and update a student’s section assignment.</p>
        </div>
        <button type="button" disabled={fetching} onClick={onRefresh}>
          <RefreshCw size={15} aria-hidden="true" />
          {fetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>
      {loading && <p role="status">Loading invitations…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && !invitations.length && <p role="status">No pending student invitations.</p>}
      {!loading && !error && invitations.length > 0 && (
        <div className="student-invitation-table-scroll">
          <table className="student-invitation-table">
            <caption className="sr-only">Pending student setup invitations</caption>
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Register No.</th>
                <th scope="col">Batch / Section</th>
                <th scope="col">Email status</th>
                <th scope="col">Expires</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {invitations.map((invite) => (
                <tr key={invite.invitation_id}>
                  <td>
                    <strong>{invite.student_name}</strong>
                    <small>{invite.email}</small>
                  </td>
                  <td>{invite.register_number}</td>
                  <td>
                    <strong>{invite.batch_code ?? invite.batch_name ?? '—'}</strong>
                    <small>{[invite.section_code, invite.section_name].filter(Boolean).join(' · ') || '—'}</small>
                  </td>
                  <td>
                    <span className={`student-invitation-status is-${invite.email_delivery_status}`}>
                      {invite.email_delivery_status === 'sent'
                        ? 'Sent'
                        : invite.email_delivery_status === 'failed'
                          ? 'Needs retry'
                          : 'Pending'}
                    </span>
                  </td>
                  <td>
                    <time dateTime={invite.expires_at}>{new Date(invite.expires_at).toLocaleDateString()}</time>
                  </td>
                  <td>
                    <div className="student-invitation-actions">
                      <button type="button" disabled={busy} onClick={() => onResend(invite.invitation_id)}>
                        Resend link
                      </button>
                      <button
                        type="button"
                        disabled={busy || !sectionId || sectionId === invite.academic_section_id}
                        onClick={() => onReassign(invite.invitation_id)}
                      >
                        Change section
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

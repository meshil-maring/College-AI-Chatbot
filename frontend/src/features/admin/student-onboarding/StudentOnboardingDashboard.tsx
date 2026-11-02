import { MailCheck, MailWarning, UserPlus, UsersRound } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { StudentInvitation } from '../../../types/admin/students.ts'
import AdminApprovals from '../students/AdminApprovals.tsx'
import StudentInvitationList from './StudentInvitationList.tsx'

export default function StudentOnboardingDashboard({
  accessToken,
  canReview,
  invitations,
  invitationsLoading,
  invitationsError,
  invitationsFetching,
  busy,
  sectionId,
  bulkOnly,
  bulkStep,
  onRefresh,
  onResend,
  onReassign,
  children,
}: {
  accessToken: string
  canReview: boolean
  invitations: StudentInvitation[]
  invitationsLoading: boolean
  invitationsError: string
  invitationsFetching: boolean
  busy: boolean
  sectionId: string
  bulkOnly: boolean
  bulkStep: number
  onRefresh: () => void
  onResend: (invitationId: string) => void
  onReassign: (invitationId: string) => void
  children: ReactNode
}) {
  const [activeTab, setActiveTab] = useState<'requests' | 'invitations'>('requests')
  const pendingCount = invitations.length
  const sentCount = invitations.filter((invitation) => invitation.email_delivery_status === 'sent').length
  const issueCount = invitations.filter((invitation) => invitation.email_delivery_status === 'failed').length
  const showRequests = canReview && activeTab === 'requests'
  const statsUnavailable = invitationsLoading || Boolean(invitationsError)
  const bulkStage = ['Academic placement', 'Upload File', 'Validate & Preview', 'Import Result'][bulkStep]

  return (
    <section
      className={`student-onboarding-dashboard${bulkOnly ? ' is-bulk-import' : ''}`}
      aria-label={bulkOnly ? 'Bulk student import' : 'Student registration'}
    >
      {bulkOnly ? (
        <header className="student-onboarding-page-heading student-onboarding-bulk-heading">
          <nav className="student-onboarding-breadcrumb" aria-label="Breadcrumb">
            <span>Students</span>
            <span aria-hidden="true">›</span>
            <span>Bulk Import</span>
            <span aria-hidden="true">›</span>
            <span aria-current="page">{bulkStage}</span>
          </nav>
          <h1>Bulk Student Import</h1>
          <p>Validate the uploaded file and review student records before importing.</p>
        </header>
      ) : (
        <header className="student-onboarding-page-heading">
          <div>
            <span className="student-onboarding-eyebrow">STUDENT MANAGEMENT</span>
            <h2>Student Registration</h2>
            <p>Register new students and manage registration requests and setup links.</p>
          </div>
          <a className="student-onboarding-register-cta" href="#student-registration-form">
            <UserPlus size={18} aria-hidden="true" />
            Register Student
          </a>
        </header>
      )}

      {!bulkOnly && (
        <div className="student-onboarding-metrics" aria-label="Invitation summary">
          <article className="student-onboarding-metric">
            <span className="student-onboarding-metric-icon">
              <UsersRound size={20} aria-hidden="true" />
            </span>
            <div>
              <strong>{statsUnavailable ? '—' : pendingCount}</strong>
              <span>Pending invitations</span>
            </div>
          </article>
          <article className="student-onboarding-metric is-success">
            <span className="student-onboarding-metric-icon">
              <MailCheck size={20} aria-hidden="true" />
            </span>
            <div>
              <strong>{statsUnavailable ? '—' : sentCount}</strong>
              <span>Setup emails sent</span>
            </div>
          </article>
          <article className="student-onboarding-metric is-warning">
            <span className="student-onboarding-metric-icon">
              <MailWarning size={20} aria-hidden="true" />
            </span>
            <div>
              <strong>{statsUnavailable ? '—' : issueCount}</strong>
              <span>Email delivery issues</span>
            </div>
          </article>
        </div>
      )}

      {bulkOnly ? (
        <div className="student-onboarding-bulk-content">{children}</div>
      ) : (
        <div className="student-onboarding-dashboard-grid">
          <section className="student-onboarding-records" aria-label="Student records">
            {canReview && (
              <div className="student-onboarding-dashboard-tabs" role="group" aria-label="Student records">
                <button type="button" aria-pressed={showRequests} onClick={() => setActiveTab('requests')}>
                  Registration Requests
                </button>
                <button type="button" aria-pressed={!showRequests} onClick={() => setActiveTab('invitations')}>
                  Pending Invitations <span>{pendingCount}</span>
                </button>
              </div>
            )}
            {showRequests ? (
              <div className="student-onboarding-records-content">
                <AdminApprovals accessToken={accessToken} />
              </div>
            ) : (
              <div className="student-onboarding-records-content">
                <StudentInvitationList
                  invitations={invitations}
                  loading={invitationsLoading}
                  error={invitationsError}
                  fetching={invitationsFetching}
                  busy={busy}
                  sectionId={sectionId}
                  onRefresh={onRefresh}
                  onResend={onResend}
                  onReassign={onReassign}
                />
              </div>
            )}
          </section>

          <aside
            className="student-onboarding-registration-card"
            id="student-registration-form"
            aria-labelledby="student-registration-form-heading"
          >
            <h3 id="student-registration-form-heading">
              <UserPlus size={20} aria-hidden="true" />
              Register Student (By Admin)
            </h3>
            {children}
          </aside>
        </div>
      )}
    </section>
  )
}

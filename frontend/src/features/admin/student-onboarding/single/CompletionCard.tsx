import { Check, Mail, RefreshCw, UserPlus } from 'lucide-react'
import StudentPageLink from '../shared/StudentPageLink.tsx'

export default function CompletionCard({
  sent,
  email,
  placementLabel,
  resending,
  onAgain,
  onChangePlacement,
  onResend,
}: {
  sent: boolean
  email: string
  placementLabel: string
  resending: boolean
  onAgain: () => void
  onChangePlacement: () => void
  /** Present when the setup email failed and the new invitation can be resent. */
  onResend?: () => void
}) {
  return (
    <div
      className={`student-onboarding-completion ${sent ? 'is-success' : 'is-warning'}`}
      role="region"
      aria-label="Registration result"
    >
      <span className="student-onboarding-completion-icon">{sent ? <Check size={24} /> : <Mail size={24} />}</span>
      <span className="student-onboarding-eyebrow">{sent ? 'INVITATION SENT' : 'DELIVERY NEEDS ATTENTION'}</span>
      <h2>{sent ? 'Student registration is underway' : 'The account was created, but the email did not send'}</h2>
      <p>
        {sent
          ? `A secure setup link was sent to ${email}. The student appears in All Students until they finish setup.`
          : `Resend the setup link now, or later from Pending invitations, for ${email}.`}
      </p>
      <div className="student-onboarding-completion-actions">
        {!sent && onResend && (
          <button type="button" className="student-onboarding-primary" disabled={resending} onClick={onResend}>
            <RefreshCw size={16} aria-hidden="true" /> {resending ? 'Resending…' : 'Resend setup link'}
          </button>
        )}
        <button
          type="button"
          className={sent ? 'student-onboarding-primary' : 'student-onboarding-secondary'}
          onClick={onAgain}
        >
          <UserPlus size={16} aria-hidden="true" /> Register another student
        </button>
        <StudentPageLink page="all" className="student-onboarding-secondary student-onboarding-link-button">
          View in All Students
        </StudentPageLink>
      </div>
      {placementLabel && (
        <p className="student-onboarding-completion-placement">
          Next student goes to <strong>{placementLabel}</strong>.{' '}
          <button type="button" className="student-onboarding-text-button" onClick={onChangePlacement}>
            Change placement
          </button>
        </p>
      )}
    </div>
  )
}

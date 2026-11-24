import { Check, Mail } from 'lucide-react'

export default function CompletionCard({
  sent,
  email,
  onAgain,
}: {
  sent: boolean
  email: string
  onAgain: () => void
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
          ? `A secure setup link was sent to ${email}.`
          : `You can resend a fresh setup link from Pending invitations for ${email}.`}
      </p>
      <button type="button" className="student-onboarding-secondary" onClick={onAgain}>
        Register another student
      </button>
    </div>
  )
}

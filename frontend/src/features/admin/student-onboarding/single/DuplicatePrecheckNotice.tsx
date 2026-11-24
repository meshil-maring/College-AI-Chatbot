import { TriangleAlert } from 'lucide-react'
import type { StudentIdentityReviewResponse } from '../../../../types/admin/students.ts'
import StudentPageLink from '../shared/StudentPageLink.tsx'
import { describeInvitation, describeStudent } from './DuplicateStudentConflictNotice.tsx'

/** Review-step warning when the entered identifiers already belong to someone in this institution. */
export default function DuplicatePrecheckNotice({
  review,
  reviewing,
  onEdit,
}: {
  review: StudentIdentityReviewResponse | null
  reviewing: boolean
  onEdit: () => void
}) {
  if (reviewing) {
    return (
      <p className="student-onboarding-precheck is-checking" role="status">
        Checking for existing students with these details…
      </p>
    )
  }
  if (!review) return null
  const matches = review.students.length + review.invitations.length
  if (!matches && !review.email_conflict_exists) return null
  return (
    <div className="student-onboarding-precheck" role="status">
      <TriangleAlert size={18} aria-hidden="true" />
      <div>
        <strong>This student may already be registered</strong>
        {matches > 0 ? (
          <ul>
            {review.students.map((student, index) => (
              <li key={`student-${index}`}>{describeStudent(student)}</li>
            ))}
            {review.invitations.map((invitation, index) => (
              <li key={`invitation-${index}`}>{describeInvitation(invitation)}</li>
            ))}
          </ul>
        ) : (
          <p>This email is already used by an account outside this institution’s student records.</p>
        )}
        <p>Creating the account will fail while these details are in use. Edit the details or check the record.</p>
        <div className="student-onboarding-precheck-actions">
          <button type="button" className="student-onboarding-text-button" onClick={onEdit}>
            Edit details
          </button>
          <StudentPageLink page="all">Open All Students</StudentPageLink>
        </div>
      </div>
    </div>
  )
}

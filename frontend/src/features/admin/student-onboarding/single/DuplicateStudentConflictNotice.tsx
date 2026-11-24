import StudentPageLink from '../shared/StudentPageLink.tsx'
import type {
  StudentIdentityAccountMatch,
  StudentIdentityInvitationMatch,
  StudentIdentityReviewResponse,
} from '../../../../types/admin/students.ts'

export default function DuplicateStudentConflictNotice({
  message,
  review,
  reviewError,
  reviewing,
}: {
  message: string
  review: StudentIdentityReviewResponse | null
  reviewError: string
  reviewing: boolean
}) {
  const matches = [...(review?.students ?? []), ...(review?.invitations ?? [])]

  return (
    <div role="alert" className="student-onboarding-inline-error">
      <p>{message}</p>
      <p>
        No new student was created. All Students only includes student accounts and pending invitations belonging to
        your institution.
      </p>
      <StudentPageLink page="all">Open All Students</StudentPageLink>
      {reviewing && <p role="status">Checking for matching student records in your institution…</p>}
      {reviewError && <p role="status">{reviewError}</p>}
      {review && matches.length > 0 && (
        <div>
          <strong>Matching institution record{matches.length === 1 ? '' : 's'}</strong>
          <ul>
            {review.students.map((student, index) => (
              <li key={`student-${index}`}>{describeStudent(student)}</li>
            ))}
            {review.invitations.map((invitation, index) => (
              <li key={`invitation-${index}`}>{describeInvitation(invitation)}</li>
            ))}
          </ul>
        </div>
      )}
      {review && matches.length === 0 && (
        <p role="status">
          No matching student or pending invitation was found in this institution.
          {review.email_conflict_exists
            ? ' The email is already used by an account, but that account has no student record here and will not appear in All Students. Contact your administrator to reconcile it.'
            : ' Check the submitted identifiers or contact your administrator to reconcile the conflict.'}
        </p>
      )}
    </div>
  )
}

export function describeStudent(student: StudentIdentityAccountMatch) {
  return `${student.student_name} · ${student.email ?? 'No email'} · Register ${student.register_number ?? '—'} · Roll ${student.university_roll_number ?? '—'} · ${student.has_signed_in ? 'Signed in' : 'Not signed in'} · Approval ${student.approval_status}`
}

export function describeInvitation(invitation: StudentIdentityInvitationMatch) {
  return `${invitation.student_name} · ${invitation.email} · Register ${invitation.register_number} · Roll ${invitation.university_roll_number ?? '—'} · Pending invitation, email ${invitation.email_delivery_status}`
}

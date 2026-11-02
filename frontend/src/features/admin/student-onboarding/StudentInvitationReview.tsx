import { Mail, UserRound } from 'lucide-react'
import type { AcademicSection } from '../../../types/academicStructure.ts'
import type { StudentInvitationInput } from '../../../types/admin/students.ts'

export default function StudentInvitationReview({
  student,
  section,
  batchCode,
}: {
  student: StudentInvitationInput
  section: AcademicSection
  batchCode: string
}) {
  return (
    <div className="student-onboarding-review">
      <div className="student-onboarding-review-heading">
        <span className="student-onboarding-review-icon">
          <UserRound size={20} />
        </span>
        <div>
          <h3>Check the student details</h3>
          <p>We’ll create a pending account and email a secure password setup link.</p>
        </div>
      </div>
      <dl className="student-onboarding-review-grid">
        <div>
          <dt>Student name</dt>
          <dd>{student.student_name}</dd>
        </div>
        <div>
          <dt>Register number</dt>
          <dd>{student.register_number}</dd>
        </div>
        <div>
          <dt>University roll number</dt>
          <dd>{student.university_roll_number || 'Not provided'}</dd>
        </div>
        <div>
          <dt>Email address</dt>
          <dd>
            <Mail size={15} />
            {student.email}
          </dd>
        </div>
      </dl>
      <div className="student-onboarding-assignment">
        <span className="student-onboarding-assignment-label">Academic placement</span>
        <strong>
          {batchCode} <span aria-hidden="true">/</span> {section.code} · {section.name}
        </strong>
        <small>The batch code is included in the setup email.</small>
      </div>
    </div>
  )
}

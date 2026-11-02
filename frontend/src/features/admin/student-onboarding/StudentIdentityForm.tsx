import type { StudentInvitationInput } from '../../../types/admin/students.ts'

export default function StudentIdentityForm({
  student,
  busy,
  hasSection,
  onFieldChange,
  onContinue,
}: {
  student: StudentInvitationInput
  busy: boolean
  hasSection: boolean
  onFieldChange: (field: keyof StudentInvitationInput, value: string) => void
  onContinue: () => void
}) {
  return (
    <form
      className="student-onboarding-identity-form"
      onSubmit={(event) => {
        event.preventDefault()
        onContinue()
      }}
    >
      <div className="student-onboarding-form-heading">
        <span className="student-onboarding-eyebrow">Student information</span>
        <h3>Enter the student’s details</h3>
        <p>Use the institution’s official records. The email will receive the password setup link.</p>
      </div>
      <div className="student-onboarding-form-grid">
        <label>
          <span>
            Student name <b aria-hidden="true">*</b>
          </span>
          <input
            required
            autoComplete="name"
            maxLength={200}
            value={student.student_name}
            disabled={busy}
            onChange={(event) => onFieldChange('student_name', event.target.value)}
          />
        </label>
        <label>
          <span>
            Register number <b aria-hidden="true">*</b>
          </span>
          <input
            required
            maxLength={128}
            placeholder="e.g. CSE8777912026"
            value={student.register_number}
            disabled={busy}
            onChange={(event) => onFieldChange('register_number', event.target.value)}
          />
        </label>
        <label>
          <span>
            University roll number <small>Optional</small>
          </span>
          <input
            maxLength={128}
            value={student.university_roll_number ?? ''}
            disabled={busy}
            onChange={(event) => onFieldChange('university_roll_number', event.target.value)}
          />
        </label>
        <label>
          <span>
            Email address <b aria-hidden="true">*</b>
          </span>
          <input
            required
            type="email"
            autoComplete="email"
            maxLength={320}
            placeholder="student@example.edu"
            value={student.email}
            disabled={busy}
            onChange={(event) => onFieldChange('email', event.target.value)}
          />
          <small>We’ll send the secure setup link to this address.</small>
        </label>
      </div>
      <div className="student-onboarding-form-footer">
        <span>
          <b aria-hidden="true">*</b> Required fields
        </span>
        <button type="submit" className="student-onboarding-primary" disabled={busy || !hasSection}>
          Review details <span aria-hidden="true">→</span>
        </button>
      </div>
    </form>
  )
}

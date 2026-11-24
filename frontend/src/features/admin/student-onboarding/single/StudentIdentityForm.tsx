import { useRef, useState } from 'react'
import type { StudentInvitationInput } from '../../../../types/admin/students.ts'
import { STUDENT_FIELD_ORDER, validateStudent, type StudentField } from './studentValidation.ts'

const FIELDS: Record<
  StudentField,
  {
    label: string
    required: boolean
    maxLength: number
    type?: string
    autoComplete?: string
    placeholder?: string
    hint?: string
  }
> = {
  student_name: { label: 'Student name', required: true, maxLength: 200, autoComplete: 'name' },
  register_number: { label: 'Register number', required: true, maxLength: 128, placeholder: 'e.g. CSE8777912026' },
  university_roll_number: { label: 'University roll number', required: false, maxLength: 128 },
  email: {
    label: 'Email address',
    required: true,
    maxLength: 320,
    type: 'email',
    autoComplete: 'email',
    placeholder: 'student@example.edu',
    hint: 'We’ll send the secure setup link to this address.',
  },
}

export default function StudentIdentityForm({
  student,
  busy,
  placementLabel,
  onFieldChange,
  onBack,
  onContinue,
}: {
  student: StudentInvitationInput
  busy: boolean
  /** Chosen batch and section; empty when no placement is selected. */
  placementLabel: string
  onFieldChange: (field: StudentField, value: string) => void
  onBack: () => void
  onContinue: () => void
}) {
  const [touched, setTouched] = useState<Partial<Record<StudentField, boolean>>>({})
  const inputs = useRef<Partial<Record<StudentField, HTMLInputElement | null>>>({})
  const errors = validateStudent(student)

  return (
    <form
      className="student-onboarding-identity-form"
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        const firstInvalid = STUDENT_FIELD_ORDER.find((field) => errors[field])
        if (firstInvalid) {
          setTouched({ student_name: true, register_number: true, email: true })
          inputs.current[firstInvalid]?.focus()
          return
        }
        onContinue()
      }}
    >
      <div className="student-onboarding-form-heading">
        <h2>Enter the student’s details</h2>
        <p>Use the institution’s official records. The email will receive the password setup link.</p>
      </div>
      {placementLabel && (
        <div className="student-onboarding-placement-summary">
          <span>
            Placing in <strong>{placementLabel}</strong>
          </span>
          <button type="button" className="student-onboarding-text-button" disabled={busy} onClick={onBack}>
            Change
          </button>
        </div>
      )}
      <div className="student-onboarding-form-grid">
        {STUDENT_FIELD_ORDER.map((field) => {
          const config = FIELDS[field]
          const error = touched[field] ? errors[field] : undefined
          const describedBy = error ? `student-${field}-error` : config.hint ? `student-${field}-hint` : undefined
          return (
            <label key={field}>
              <span>
                {config.label} {config.required ? <b aria-hidden="true">*</b> : <small>Optional</small>}
              </span>
              <input
                ref={(element) => {
                  inputs.current[field] = element
                }}
                required={config.required}
                type={config.type ?? 'text'}
                autoComplete={config.autoComplete}
                maxLength={config.maxLength}
                placeholder={config.placeholder}
                value={student[field] ?? ''}
                disabled={busy}
                aria-invalid={error ? true : undefined}
                aria-describedby={describedBy}
                onChange={(event) => onFieldChange(field, event.target.value)}
                onBlur={() => setTouched((current) => ({ ...current, [field]: true }))}
              />
              {error ? (
                <small id={`student-${field}-error`} className="student-onboarding-field-error">
                  {error}
                </small>
              ) : (
                config.hint && <small id={`student-${field}-hint`}>{config.hint}</small>
              )}
            </label>
          )
        })}
      </div>
      <div className="student-onboarding-form-footer">
        <span>
          <b aria-hidden="true">*</b> Required fields
        </span>
        <div>
          <button type="button" className="student-onboarding-secondary" disabled={busy} onClick={onBack}>
            Back
          </button>
          <button type="submit" className="student-onboarding-primary" disabled={busy || !placementLabel}>
            Review details <span aria-hidden="true">→</span>
          </button>
        </div>
      </div>
    </form>
  )
}

import { SELECT_CLASS } from '../StaffFacultyUI.tsx'
import type { AdminProfileDraft, AdminProfileErrors } from './adminProfile.ts'

const FIELDS: readonly {
  name: keyof AdminProfileDraft
  label: string
  type?: string
  maxLength?: number
  optional?: boolean
}[] = [
  { name: 'employee_id', label: 'Employee ID', maxLength: 40 },
  { name: 'designation', label: 'Designation', maxLength: 120 },
  { name: 'joining_date', label: 'Joining date', type: 'date' },
  { name: 'phone', label: 'Phone', type: 'tel', maxLength: 32, optional: true },
]

interface Props {
  idPrefix: string
  draft: AdminProfileDraft
  errors: AdminProfileErrors
  disabled?: boolean
  onChange: (draft: AdminProfileDraft) => void
}

/** Employee ID, designation, joining date and phone of an administrator. */
export default function AdminProfileFields({ idPrefix, draft, errors, disabled = false, onChange }: Props) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {FIELDS.map((field) => {
        const id = `${idPrefix}-${field.name}`
        const error = errors[field.name]
        return (
          <div key={field.name} className="flex flex-col gap-1 text-sm">
            <label htmlFor={id} className="font-medium text-content">
              {field.label}
              {field.optional ? <span className="font-normal text-muted"> (optional)</span> : null}
            </label>
            <input
              id={id}
              type={field.type ?? 'text'}
              value={draft[field.name]}
              maxLength={field.maxLength}
              disabled={disabled}
              autoComplete="off"
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? `${id}-error` : undefined}
              onChange={(event) => onChange({ ...draft, [field.name]: event.target.value })}
              className={`${SELECT_CLASS} aria-[invalid=true]:border-danger`}
            />
            {error ? (
              <span id={`${id}-error`} className="text-xs text-danger">
                {error}
              </span>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

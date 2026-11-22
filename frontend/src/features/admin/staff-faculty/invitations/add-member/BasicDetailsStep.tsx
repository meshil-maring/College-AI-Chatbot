import { TextField } from './FormFields.tsx'
import type { AddMemberDraftModel } from './useAddMemberDraft.ts'

const ROLES = [
  ['faculty', 'Teacher / Faculty', 'Teaching, attendance and examinations. Can later be made Head of Department.'],
  ['staff', 'Staff', 'Non-teaching administrative and institutional work.'],
] as const

/** Step 1: details shared by every member type, and the member type itself. */
export default function BasicDetailsStep({ model, idPrefix }: { model: AddMemberDraftModel; idPrefix: string }) {
  const field = { model, idPrefix }
  return (
    <>
      <TextField {...field} name="full_name" label="Full name" required maxLength={200} />
      <TextField {...field} name="email" label="Email" type="email" required maxLength={320} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField {...field} name="employee_id" label="Employee ID" required maxLength={40} />
        <TextField {...field} name="phone" label="Phone" type="tel" maxLength={32} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          {...field}
          name="designation"
          label="Designation"
          required
          maxLength={120}
          hint="For example Assistant Professor or Office Assistant."
        />
        <TextField {...field} name="joining_date" label="Joining date" type="date" required />
      </div>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium text-content">User type</legend>
        {ROLES.map(([value, label, hint]) => (
          <label key={value} className="flex cursor-pointer items-start gap-3 text-sm">
            <input
              type="radio"
              name={`${idPrefix}-role`}
              value={value}
              checked={model.draft.role === value}
              onChange={() => model.update('role', value)}
              className="mt-0.5 size-5 accent-[var(--ui-accent)]"
            />
            <span className="flex flex-col">
              <span className="text-content">{label}</span>
              <span className="text-xs text-muted">{hint}</span>
            </span>
          </label>
        ))}
        <p className="text-xs text-muted">Administrator accounts are managed separately.</p>
      </fieldset>
    </>
  )
}

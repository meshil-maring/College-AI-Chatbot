import { X } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MemberInvitationCreate, MembershipRole } from '../../../../types/admin.ts'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import { BUTTON_CLASS, PRIMARY_BUTTON_CLASS, SELECT_CLASS } from '../StaffFacultyUI.tsx'

export type InvitationDraft = Partial<MemberInvitationCreate>

interface Props {
  departments: Department[]
  initial?: InvitationDraft
  sending: boolean
  /** Resolves to an error message to show, or null when the invitation was sent. */
  onSubmit: (draft: MemberInvitationCreate) => Promise<string | null>
  onClose: () => void
}

type Field = 'full_name' | 'email' | 'department_id'

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Invite a new Staff or Faculty member; they set their own password from the email link. */
export default function AddMemberDialog({ departments, initial, sending, onSubmit, onClose }: Props) {
  const ref = useWorkspaceDialog('#staff-faculty-add-member')
  const id = useId()
  const [fullName, setFullName] = useState(initial?.full_name ?? '')
  const [email, setEmail] = useState(initial?.email ?? '')
  const [role, setRole] = useState<MembershipRole>(initial?.role ?? 'faculty')
  const listed = departments.some((department) => department.department_id === initial?.department_id)
  const [departmentId, setDepartmentId] = useState(listed ? (initial?.department_id ?? '') : '')
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({})
  const [serverError, setServerError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next: Partial<Record<Field, string>> = {}
    if (!fullName.trim()) next.full_name = 'Enter their name.'
    if (!EMAIL.test(email.trim())) next.email = 'Enter a valid email address.'
    if (!departmentId) next.department_id = 'Choose a department.'
    setErrors(next)
    setServerError(null)
    if (Object.keys(next).length) return
    const failure = await onSubmit({
      full_name: fullName.trim(),
      email: email.trim().toLowerCase(),
      role,
      department_id: departmentId,
    })
    if (failure) setServerError(failure)
    else onClose()
  }

  function field(name: Field) {
    return errors[name]
      ? { 'aria-invalid': true as const, 'aria-describedby': `${id}-${name}-error` }
      : { 'aria-invalid': false as const }
  }

  function fieldError(name: Field) {
    return errors[name] ? (
      <span id={`${id}-${name}-error`} className="text-xs text-danger">
        {errors[name]}
      </span>
    ) : null
  }

  const labelClass = 'flex flex-col gap-1 text-sm font-medium text-content'
  const inputClass = `${SELECT_CLASS} w-full aria-[invalid=true]:border-danger`

  return (
    <dialog
      ref={ref}
      aria-labelledby={`${id}-title`}
      onCancel={(event) => {
        event.preventDefault()
        if (!sending) onClose()
      }}
      className="m-auto w-[min(480px,100vw)] rounded-xl border border-line bg-surface p-0 text-content shadow-overlay backdrop:bg-[var(--ui-overlay)]"
    >
      <form noValidate onSubmit={(event) => void submit(event)} className="flex max-h-[min(720px,100dvh)] flex-col">
        <header className="flex items-start gap-3 border-b border-line p-5">
          <div className="mr-auto">
            <h2 id={`${id}-title`} className="text-section font-semibold">
              Add Staff or Faculty
            </h2>
            <p className="mt-1 text-sm text-muted">
              We email them a link to set their password. They join your institution once they accept.
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            disabled={sending}
            onClick={onClose}
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg hover:bg-hover"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </header>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          {serverError ? (
            <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
              {serverError}
            </p>
          ) : null}
          <label className={labelClass}>
            <span>
              Full name <span aria-hidden="true">*</span>
            </span>
            <input
              value={fullName}
              autoComplete="off"
              maxLength={200}
              onChange={(event) => setFullName(event.target.value)}
              className={inputClass}
              {...field('full_name')}
            />
            {fieldError('full_name')}
          </label>
          <label className={labelClass}>
            <span>
              Email <span aria-hidden="true">*</span>
            </span>
            <input
              type="email"
              value={email}
              autoComplete="off"
              maxLength={320}
              onChange={(event) => setEmail(event.target.value)}
              className={inputClass}
              {...field('email')}
            />
            {fieldError('email')}
          </label>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-medium text-content">Role</legend>
            {(
              [
                ['faculty', 'Faculty (Teacher)', 'Teaches; can be made Head of Department.'],
                ['staff', 'Staff', 'Administrative work; extra duties through Permissions.'],
              ] as const
            ).map(([value, label, hint]) => (
              <label key={value} className="flex cursor-pointer items-start gap-3 text-sm">
                <input
                  type="radio"
                  name={`${id}-role`}
                  value={value}
                  checked={role === value}
                  onChange={() => setRole(value)}
                  className="mt-0.5 size-5 accent-[var(--ui-accent)]"
                />
                <span className="flex flex-col">
                  <span className="text-content">{label}</span>
                  <span className="text-xs text-muted">{hint}</span>
                </span>
              </label>
            ))}
          </fieldset>
          <label className={labelClass}>
            <span>
              Department <span aria-hidden="true">*</span>
            </span>
            <select
              value={departmentId}
              disabled={departments.length === 0}
              onChange={(event) => setDepartmentId(event.target.value)}
              className={inputClass}
              {...field('department_id')}
            >
              <option value="">Choose department…</option>
              {departments.map((department) => (
                <option key={department.department_id} value={department.department_id}>
                  {department.name} ({department.code})
                </option>
              ))}
            </select>
            {departments.length === 0 ? (
              <span className="text-xs text-warning">Add an active department in Academic Setup first.</span>
            ) : null}
            {fieldError('department_id')}
          </label>
        </div>
        <footer className="flex flex-wrap justify-end gap-2 border-t border-line p-5">
          <button type="button" disabled={sending} onClick={onClose} className={BUTTON_CLASS}>
            Cancel
          </button>
          <button type="submit" disabled={sending || departments.length === 0} className={PRIMARY_BUTTON_CLASS}>
            {sending ? 'Sending…' : 'Send invitation'}
          </button>
        </footer>
      </form>
    </dialog>
  )
}

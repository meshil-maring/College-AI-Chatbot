import { useId, useState, type FormEvent } from 'react'
import type { AdminAccessArea } from '../../../../types/admin/administrators.ts'
import { PRIMARY_BUTTON_CLASS, SELECT_CLASS } from '../StaffFacultyUI.tsx'
import AccessAreasField from './AccessAreasField.tsx'
import { ALL_AREAS, toAccess } from './accessAreas.ts'
import type { InstitutionAdminsModel } from './useInstitutionAdmins.ts'

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Owner only: invite a new administrator, who sets their own password from the email. */
export default function InviteAdminForm({ model }: { model: InstitutionAdminsModel }) {
  const id = useId()
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [touched, setTouched] = useState(false)
  const [areas, setAreas] = useState<AdminAccessArea[]>(ALL_AREAS)
  const invalid = !EMAIL.test(email.trim())
  const sending = model.actionKey === 'invite'

  async function submit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (invalid) return
    const failure = await model.invite(email, fullName, toAccess(areas))
    if (!failure) {
      setEmail('')
      setFullName('')
      setAreas(ALL_AREAS)
      setTouched(false)
    }
  }

  return (
    <form
      noValidate
      aria-labelledby={`${id}-title`}
      onSubmit={(event) => void submit(event)}
      className="space-y-3 rounded-xl border border-line bg-surface p-4"
    >
      <h3 id={`${id}-title`} className="text-sm font-semibold text-content">
        Invite an administrator
      </h3>
      <p className="text-sm text-muted">
        Administrators manage the institution. Untick areas to limit what this administrator can do; you can change it
        later.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-medium text-content">
          Email
          <input
            type="email"
            value={email}
            autoComplete="off"
            maxLength={320}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={touched && invalid}
            aria-describedby={touched && invalid ? `${id}-email-error` : undefined}
            className={`${SELECT_CLASS} aria-[invalid=true]:border-danger`}
          />
          {touched && invalid ? (
            <span id={`${id}-email-error`} className="text-xs text-danger">
              Enter a valid email address.
            </span>
          ) : null}
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-content">
          <span>
            Full name <span className="font-normal text-muted">(optional)</span>
          </span>
          <input
            value={fullName}
            autoComplete="off"
            maxLength={200}
            onChange={(event) => setFullName(event.target.value)}
            className={SELECT_CLASS}
          />
        </label>
      </div>
      <AccessAreasField legend="Access" value={areas} disabled={sending} onChange={setAreas} />
      <div className="flex justify-end">
        <button type="submit" disabled={sending} className={PRIMARY_BUTTON_CLASS}>
          {sending ? 'Sending…' : 'Send invitation'}
        </button>
      </div>
    </form>
  )
}

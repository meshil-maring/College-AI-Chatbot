import { X } from 'lucide-react'
import { useId, type FormEvent } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import { TextField } from '../invitations/add-member/FormFields.tsx'
import RoleDetailsStep from '../invitations/add-member/RoleDetailsStep.tsx'
import { BUTTON_CLASS, PRIMARY_BUTTON_CLASS, roleLabel } from '../StaffFacultyUI.tsx'
import { useEditProfile } from './useEditProfile.ts'

interface Props {
  accessToken: string
  member: MembershipRosterEntry
  departments: Department[]
  onSaved: (message: string) => void
  onClose: () => void
}

/**
 * Edit an existing member's employee profile and departments. Name and email
 * are their sign-in identity, and the role is changed from the roster.
 */
export default function EditProfileDialog({ accessToken, member, departments, onSaved, onClose }: Props) {
  const ref = useWorkspaceDialog('#membership-roster-heading')
  const id = useId()
  const model = useEditProfile(accessToken, member)
  const name = member.name || member.email

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (await model.save()) onSaved(`Profile of ${name} saved.`)
  }

  return (
    <dialog
      ref={ref}
      aria-labelledby={`${id}-title`}
      onCancel={(event) => {
        event.preventDefault()
        if (!model.saving) onClose()
      }}
      className="m-auto w-[min(640px,100vw)] rounded-xl border border-line bg-surface p-0 text-content shadow-overlay backdrop:bg-[var(--ui-overlay)]"
    >
      <form noValidate onSubmit={(event) => void submit(event)} className="flex max-h-[min(760px,100dvh)] flex-col">
        <header className="flex items-start gap-3 border-b border-line p-5">
          <div className="mr-auto min-w-0">
            <h2 id={`${id}-title`} className="text-section font-semibold">
              Edit profile
            </h2>
            <p className="mt-1 break-all text-sm text-muted">
              {name} · {member.email} · {roleLabel(member.role)}
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            disabled={model.saving}
            onClick={onClose}
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg hover:bg-hover"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </header>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          {model.serverError ? (
            <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
              {model.serverError}
            </p>
          ) : null}
          {model.loadError ? (
            <p role="alert" className="text-sm text-danger">
              {model.loadError}
            </p>
          ) : null}
          {model.draft ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField {...fields(model, id)} name="employee_id" label="Employee ID" required maxLength={40} />
                <TextField {...fields(model, id)} name="phone" label="Phone" type="tel" maxLength={32} />
                <TextField {...fields(model, id)} name="designation" label="Designation" required maxLength={120} />
                <TextField {...fields(model, id)} name="joining_date" label="Joining date" type="date" required />
              </div>
              <RoleDetailsStep model={fields(model, id).model} idPrefix={id} departments={departments} />
            </>
          ) : model.loading ? (
            <p role="status" className="text-sm text-muted">
              Loading profile…
            </p>
          ) : null}
        </div>
        <footer className="flex flex-wrap justify-end gap-2 border-t border-line p-5">
          <button type="button" disabled={model.saving} onClick={onClose} className={BUTTON_CLASS}>
            Cancel
          </button>
          <button type="submit" disabled={model.saving || !model.draft} className={PRIMARY_BUTTON_CLASS}>
            {model.saving ? 'Saving…' : 'Save profile'}
          </button>
        </footer>
      </form>
    </dialog>
  )
}

/** The loaded draft as the shared form fields expect it. */
function fields(model: ReturnType<typeof useEditProfile>, idPrefix: string) {
  return { model: { draft: model.draft!, errors: model.errors, update: model.update }, idPrefix }
}

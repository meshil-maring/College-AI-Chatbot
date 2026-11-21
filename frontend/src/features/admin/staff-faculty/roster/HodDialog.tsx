import { X } from 'lucide-react'
import { useState } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import { BUTTON_CLASS, PRIMARY_BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import type { HeadAppointment } from '../useDepartmentHeadActions.ts'

interface Props {
  member: MembershipRosterEntry
  departments: Department[]
  appointments: HeadAppointment[]
  coHeadsOf: (departmentId: string, exceptUserId: string) => string[]
  canAppoint: boolean
  saving: boolean
  onSave: (departmentIds: string[]) => void
  onClose: () => void
}

/**
 * Choose every department a faculty member heads. Departments may have more
 * than one Head of Department; all heads have the same authority.
 */
export default function HodDialog({
  member,
  departments,
  appointments,
  coHeadsOf,
  canAppoint,
  saving,
  onSave,
  onClose,
}: Props) {
  const ref = useWorkspaceDialog('#membership-roster-heading')
  const name = member.name || member.email
  const initial = appointments.map((item) => item.departmentId)
  const [selected, setSelected] = useState<string[]>(initial)
  const changed = selected.length !== initial.length || selected.some((id) => !initial.includes(id))
  // Ended or deactivated departments the member still heads can only be removed.
  const inactive = appointments.filter((item) => !item.departmentActive)

  function toggle(id: string, checked: boolean) {
    setSelected((previous) => (checked ? [...previous, id] : previous.filter((item) => item !== id)))
  }

  function option(id: string, label: string, disabled: boolean) {
    const others = coHeadsOf(id, member.user_id)
    return (
      <li key={id}>
        <label className="flex cursor-pointer items-start gap-3 px-3 py-2 hover:bg-hover">
          <input
            type="checkbox"
            className="mt-0.5 size-5 shrink-0 accent-[var(--ui-accent)]"
            checked={selected.includes(id)}
            disabled={saving || (disabled && !selected.includes(id))}
            onChange={(event) => toggle(id, event.target.checked)}
          />
          <span className="flex min-w-0 flex-col">
            <span className="text-sm text-content">
              {label}
              {member.department_id === id ? <span className="ml-2 text-xs text-muted">(home department)</span> : null}
            </span>
            <span className="text-xs text-muted">
              {others.length ? `Also headed by ${others.join(', ')}` : 'No other Head of Department'}
            </span>
          </span>
        </label>
      </li>
    )
  }

  return (
    <dialog
      ref={ref}
      aria-labelledby="hod-dialog-title"
      aria-describedby="hod-dialog-description"
      onCancel={(event) => {
        event.preventDefault()
        if (!saving) onClose()
      }}
      className="m-auto flex max-h-[min(640px,100dvh)] w-[min(480px,100vw)] flex-col rounded-xl border border-line bg-surface p-0 text-content shadow-overlay backdrop:bg-[var(--ui-overlay)]"
    >
      <header className="flex items-start gap-3 border-b border-line p-5">
        <div className="mr-auto">
          <h2 id="hod-dialog-title" className="text-section font-semibold">
            Head of Department
          </h2>
          <p id="hod-dialog-description" className="mt-1 text-sm text-muted">
            Choose every department {name} heads. A department can have more than one Head of Department; each can
            review its student transfers.
          </p>
        </div>
        <button
          type="button"
          aria-label="Close"
          disabled={saving}
          onClick={onClose}
          className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg hover:bg-hover"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {!canAppoint ? (
          <p className="mb-3 rounded-lg border border-warning bg-warning-bg p-3 text-sm text-warning">
            Only active Faculty can be appointed. You can still end existing appointments.
          </p>
        ) : null}
        {departments.length === 0 && inactive.length === 0 ? (
          <p className="text-sm text-muted">No active departments yet. Add one in Academic Setup first.</p>
        ) : (
          <fieldset>
            <legend className="sr-only">Departments headed by {name}</legend>
            <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
              {departments.map((department) =>
                option(department.department_id, `${department.name} (${department.code})`, !canAppoint),
              )}
              {inactive.map((item) => option(item.departmentId, item.departmentName, true))}
            </ul>
          </fieldset>
        )}
      </div>
      <footer className="flex flex-wrap justify-end gap-2 border-t border-line p-5">
        <button type="button" disabled={saving} onClick={onClose} className={BUTTON_CLASS}>
          Cancel
        </button>
        <button
          type="button"
          disabled={saving || !changed}
          onClick={() => onSave(selected)}
          className={PRIMARY_BUTTON_CLASS}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
      </footer>
    </dialog>
  )
}

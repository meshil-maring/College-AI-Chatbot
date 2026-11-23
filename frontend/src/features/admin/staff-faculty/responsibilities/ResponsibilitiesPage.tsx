import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import { Feedback } from '../StaffFacultyUI.tsx'
import AssignResponsibilityForm from './AssignResponsibilityForm.tsx'
import ResponsibilityList from './ResponsibilityList.tsx'
import { useMemberResponsibilities } from './useMemberResponsibilities.ts'

interface Props {
  accessToken: string
  members: MembershipRosterEntry[]
  /** People who currently head at least one department. */
  headCount: number
  allowMultiHod: boolean
  onOpenRoster: () => void
}

/**
 * Responsibilities are extra duties of a Faculty member, not roles: Head of
 * Department, Class In-Charge and Subject Coordinator. HODs are appointed from
 * the roster; this page sets the institution's HOD rule and manages the others.
 */
export default function ResponsibilitiesPage({ accessToken, members, headCount, allowMultiHod, onOpenRoster }: Props) {
  const model = useMemberResponsibilities(accessToken)
  const faculty = members
    .filter((member) => member.role === 'faculty' && member.status === 'active')
    .sort((a, b) => (a.name || a.email).localeCompare(b.name || b.email))

  return (
    <div className="space-y-4">
      <Feedback error={model.error} onDismiss={model.dismiss} />
      <section aria-labelledby="hod-policy-heading" className="space-y-3 rounded-xl border border-line bg-surface p-4">
        <h3 id="hod-policy-heading" className="text-sm font-semibold text-content">
          Heads of Department
        </h3>
        <p className="text-sm text-muted">
          {headCount === 1 ? '1 faculty member heads' : `${headCount} faculty members head`} a department. Appoint or
          change Heads of Department, and their start and planned end dates, from the{' '}
          <button type="button" onClick={onOpenRoster} className="font-semibold text-accent underline">
            Roster
          </button>
          .
        </p>
        <label className="flex cursor-pointer items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={allowMultiHod}
            disabled={model.actionKey === 'policy'}
            onChange={(event) => void model.setPolicy(event.target.checked)}
            className="mt-0.5 size-5 accent-[var(--ui-accent)]"
          />
          <span className="flex flex-col">
            <span className="text-content">Allow one faculty member to head more than one department</span>
            <span className="text-xs text-muted">
              Applies to new appointments. Turning it off keeps existing appointments.
            </span>
          </span>
        </label>
      </section>
      {model.targetsError ? (
        <p role="alert" className="text-sm text-danger">
          {model.targetsError}
        </p>
      ) : null}
      <AssignResponsibilityForm model={model} faculty={faculty} />
      <ResponsibilityList model={model} />
      <p className="text-xs text-muted">
        Class In-Charge and Subject Coordinator are recorded for planning; they do not unlock extra screens yet.
      </p>
    </div>
  )
}

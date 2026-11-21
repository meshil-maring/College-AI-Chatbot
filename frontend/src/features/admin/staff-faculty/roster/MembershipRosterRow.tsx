import { Crown, KeyRound } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRole, MembershipRosterEntry } from '../../../../types/admin.ts'
import {
  Badge,
  BUTTON_CLASS,
  DANGER_BUTTON_CLASS,
  Initials,
  ROLE_OPTIONS,
  SELECT_CLASS,
  StatusBadge,
} from '../StaffFacultyUI.tsx'
import type { HeadAppointment } from '../useDepartmentHeadActions.ts'

export interface RosterActions {
  actionKey: string | null
  lifecycle: (member: MembershipRosterEntry, action: 'deactivate' | 'reactivate') => Promise<void>
  changeDepartment: (member: MembershipRosterEntry, departmentId: string) => Promise<void>
  changeRole: (member: MembershipRosterEntry, role: MembershipRole) => Promise<void>
  appointmentsOf: (member: MembershipRosterEntry) => HeadAppointment[]
  /** Omitted when the administrator cannot manage Staff permissions. */
  managePermissions?: (member: MembershipRosterEntry) => void
}

function Saving({ show }: { show: boolean }) {
  return show ? (
    <span role="status" className="mt-1 block text-xs text-muted">
      Saving…
    </span>
  ) : null
}

/** One roster member: identity, editable role and department, status and actions. */
export default function MembershipRosterRow({
  member,
  departments,
  actions,
}: {
  member: MembershipRosterEntry
  departments: Department[]
  actions: RosterActions & { openHod: (member: MembershipRosterEntry) => void }
}) {
  const { actionKey, appointmentsOf, managePermissions } = actions
  const label = member.name || member.email
  const busy = actionKey !== null
  const assignedIsListed = departments.some((item) => item.department_id === member.department_id)
  const appointments = appointmentsOf(member)
  const isActive = member.status === 'active'
  // Active Faculty can be appointed; anyone still holding an appointment can have it ended.
  const canManageHod = (member.role === 'faculty' && isActive) || appointments.length > 0
  const inactive = member.status === 'inactive' || member.status === 'deactivated'

  return (
    <tr className={`border-t border-line align-top hover:bg-hover/40 ${inactive ? 'text-muted' : ''}`}>
      <td className="px-4 py-3">
        <div className="flex items-start gap-3">
          <Initials name={label} />
          <div className="min-w-0">
            <p className="font-medium text-content">{member.name || 'Pending setup'}</p>
            <p className="break-all text-xs text-muted">{member.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <select
          aria-label={`Role for ${label}`}
          value={member.role}
          disabled={busy}
          onChange={(event) => void actions.changeRole(member, event.target.value as MembershipRole)}
          className={SELECT_CLASS}
        >
          {ROLE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {appointments.length ? (
          <span className="mt-2 flex flex-wrap gap-1">
            {appointments.map((appointment) => (
              <Badge key={appointment.departmentId} tone="accent">
                <Crown aria-hidden="true" className="mr-1 size-3" />
                HOD · {appointment.departmentName}
              </Badge>
            ))}
          </span>
        ) : null}
        <Saving show={actionKey === `role:${member.user_id}`} />
      </td>
      <td className="px-4 py-3">
        <select
          aria-label={`Department for ${label}`}
          value={member.department_id ?? ''}
          disabled={busy || departments.length === 0}
          onChange={(event) => void actions.changeDepartment(member, event.target.value)}
          className={`${SELECT_CLASS} w-full max-w-64 ${member.department_id === null ? 'border-warning' : ''}`}
        >
          {member.department_id === null ? <option value="">Not set</option> : null}
          {member.department_id !== null && !assignedIsListed ? (
            <option value={member.department_id}>{member.department_name ?? 'Inactive department'}</option>
          ) : null}
          {departments.map((department) => (
            <option key={department.department_id} value={department.department_id}>
              {department.name} ({department.code})
            </option>
          ))}
        </select>
        <Saving show={actionKey === `department:${member.user_id}`} />
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={member.status} />
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap justify-end gap-2">
          {canManageHod ? (
            <button
              type="button"
              disabled={busy}
              aria-label={`Manage HOD for ${label}`}
              onClick={() => actions.openHod(member)}
              className={BUTTON_CLASS}
            >
              <Crown aria-hidden="true" className="size-4" />
              {actionKey === `hod:${member.user_id}` ? 'Saving…' : 'Manage HOD'}
            </button>
          ) : null}
          {managePermissions && member.role === 'staff' && isActive ? (
            <button type="button" disabled={busy} onClick={() => managePermissions(member)} className={BUTTON_CLASS}>
              <KeyRound aria-hidden="true" className="size-4" />
              Permissions
            </button>
          ) : null}
          {member.user_id && isActive ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void actions.lifecycle(member, 'deactivate')}
              className={DANGER_BUTTON_CLASS}
            >
              {actionKey === `deactivate:${member.user_id}` ? 'Deactivating…' : 'Deactivate'}
            </button>
          ) : null}
          {member.user_id && inactive ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void actions.lifecycle(member, 'reactivate')}
              className={BUTTON_CLASS}
            >
              {actionKey === `reactivate:${member.user_id}` ? 'Reactivating…' : 'Reactivate'}
            </button>
          ) : null}
        </div>
      </td>
    </tr>
  )
}

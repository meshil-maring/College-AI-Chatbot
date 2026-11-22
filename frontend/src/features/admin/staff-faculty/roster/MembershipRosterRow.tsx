import { Crown, History, KeyRound, CirclePause, UserCheck, UserPen, UserX } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRole, MembershipRosterEntry } from '../../../../types/admin.ts'
import { Badge, Initials, ROLE_OPTIONS, SELECT_CLASS, StatusBadge } from '../StaffFacultyUI.tsx'
import { employmentTypes } from '../invitations/add-member/memberDraft.ts'
import type { HeadAppointment } from '../useDepartmentHeadActions.ts'
import RowActionsMenu, { type RowAction } from './RowActionsMenu.tsx'

export interface RosterActions {
  actionKey: string | null
  lifecycle: (member: MembershipRosterEntry, action: 'deactivate' | 'reactivate' | 'suspend') => Promise<void>
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
  actions: RosterActions & {
    openHod: (member: MembershipRosterEntry) => void
    openProfile: (member: MembershipRosterEntry) => void
    openHistory: (member: MembershipRosterEntry) => void
  }
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
  const suspended = member.status === 'suspended'
  const employment = member.employment_type ? employmentTypes(member.role)[member.employment_type] : null

  const menu: RowAction[] = [
    {
      key: 'profile',
      label: 'Edit profile',
      icon: <UserPen aria-hidden="true" className="size-4" />,
      onSelect: () => actions.openProfile(member),
    },
    {
      key: 'history',
      label: 'History',
      icon: <History aria-hidden="true" className="size-4" />,
      onSelect: () => actions.openHistory(member),
    },
  ]
  if (canManageHod)
    menu.push({
      key: 'hod',
      label: 'Manage HOD',
      icon: <Crown aria-hidden="true" className="size-4" />,
      onSelect: () => actions.openHod(member),
    })
  if (managePermissions && member.role === 'staff' && isActive)
    menu.push({
      key: 'permissions',
      label: 'Permissions',
      icon: <KeyRound aria-hidden="true" className="size-4" />,
      onSelect: () => managePermissions(member),
    })
  if (member.user_id && isActive)
    menu.push({
      key: 'suspend',
      label: 'Suspend',
      icon: <CirclePause aria-hidden="true" className="size-4" />,
      onSelect: () => void actions.lifecycle(member, 'suspend'),
    })
  if (member.user_id && (isActive || suspended))
    menu.push({
      key: 'deactivate',
      label: 'Deactivate',
      icon: <UserX aria-hidden="true" className="size-4" />,
      danger: true,
      onSelect: () => void actions.lifecycle(member, 'deactivate'),
    })
  if (member.user_id && (inactive || suspended))
    menu.push({
      key: 'reactivate',
      label: 'Reactivate',
      icon: <UserCheck aria-hidden="true" className="size-4" />,
      onSelect: () => void actions.lifecycle(member, 'reactivate'),
    })
  // While one of this member's actions saves, the button says what is happening.
  const busyText: Record<string, string> = {
    [`hod:${member.user_id}`]: 'Saving HOD…',
    [`deactivate:${member.user_id}`]: 'Deactivating…',
    [`suspend:${member.user_id}`]: 'Suspending…',
    [`reactivate:${member.user_id}`]: 'Reactivating…',
  }

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
      <td data-label="Employee" className="px-4 py-3 text-sm">
        <p className={member.employee_id ? 'text-content' : 'text-warning'}>
          {member.employee_id ?? 'Profile not completed'}
        </p>
        {member.designation ? <p className="text-xs text-muted">{member.designation}</p> : null}
        {employment ? (
          <p className="text-xs text-muted">
            {employment}
            {member.employment_status === 'contract_ended' ? ' · contract ended' : ''}
          </p>
        ) : null}
      </td>
      <td data-label="Role" className="px-4 py-3">
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
      <td data-label="Department" className="px-4 py-3">
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
        {member.additional_department_names?.length ? (
          <p className="mt-1 text-xs text-muted">Also: {member.additional_department_names.join(', ')}</p>
        ) : null}
        <Saving show={actionKey === `department:${member.user_id}`} />
      </td>
      <td data-label="Status" className="whitespace-nowrap px-4 py-3">
        <StatusBadge status={member.status} />
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <div className="flex justify-end">
          <RowActionsMenu label={label} actions={menu} disabled={busy} busyText={busyText[actionKey ?? ''] ?? null} />
        </div>
      </td>
    </tr>
  )
}

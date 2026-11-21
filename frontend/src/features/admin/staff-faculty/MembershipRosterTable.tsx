import type { Department } from '../../../types/academicSetup.ts'
import type { MembershipRole, MembershipRosterEntry } from '../../../types/admin.ts'
import { BUTTON_CLASS, ROLE_OPTIONS, SELECT_CLASS } from './MembershipRequests.tsx'
import type { HeadAppointment } from './useDepartmentHeadActions.ts'

interface Props {
  members: MembershipRosterEntry[]
  departments: Department[]
  loading: boolean
  actionKey: string | null
  lifecycle: (member: MembershipRosterEntry, action: 'deactivate' | 'reactivate') => Promise<void>
  changeDepartment: (member: MembershipRosterEntry, departmentId: string) => Promise<void>
  changeRole: (member: MembershipRosterEntry, role: MembershipRole) => Promise<void>
  headOf: (member: MembershipRosterEntry) => HeadAppointment | null
  makeHod: (member: MembershipRosterEntry) => Promise<void>
  removeHod: (member: MembershipRosterEntry) => Promise<void>
  /** Omitted when the administrator cannot manage Staff permissions. */
  managePermissions?: (member: MembershipRosterEntry) => void
}

/**
 * Approved Staff and Faculty with the role and department the administrator
 * assigned. Faculty can also be made Head of Department of their department.
 */
export default function MembershipRosterTable({
  members,
  departments,
  loading,
  actionKey,
  lifecycle,
  changeDepartment,
  changeRole,
  headOf,
  makeHod,
  removeHod,
  managePermissions,
}: Props) {
  return (
    <section aria-labelledby="membership-roster-heading" className="rounded-xl border border-line bg-surface p-4">
      <h2 id="membership-roster-heading" className="font-semibold text-content text-section">
        Roster
      </h2>
      <p className="mt-2 text-sm text-muted">
        Change a member&apos;s role or department here. Make HOD appoints a Faculty member as Head of their department.
        Use Permissions to give a Staff member extra duties.
      </p>
      {loading ? (
        <p role="status" className="mt-4 text-sm text-muted">
          Loading roster…
        </p>
      ) : members.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No staff or faculty are on the roster yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-xs uppercase text-muted">
              <tr>
                <th className="p-2">Name</th>
                <th className="p-2">Email</th>
                <th className="p-2">Role</th>
                <th className="p-2">Department</th>
                <th className="p-2">Status</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => {
                const label = member.name || member.email
                const assignedIsListed = departments.some((item) => item.department_id === member.department_id)
                const appointment = headOf(member)
                const canBeHead = member.role === 'faculty' && member.status === 'active'
                return (
                  <tr key={member.user_id} className="border-t border-line">
                    <td className="p-2 text-content">{member.name || 'Pending setup'}</td>
                    <td className="p-2 text-muted">{member.email}</td>
                    <td className="p-2">
                      <select
                        aria-label={`Role for ${label}`}
                        value={member.role}
                        disabled={actionKey !== null}
                        onChange={(event) => void changeRole(member, event.target.value as MembershipRole)}
                        className={SELECT_CLASS}
                      >
                        {ROLE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      {appointment ? (
                        <span className="mt-1 block text-xs font-semibold text-accent">
                          HOD · {appointment.departmentName}
                        </span>
                      ) : null}
                    </td>
                    <td className="p-2">
                      <select
                        aria-label={`Department for ${label}`}
                        value={member.department_id ?? ''}
                        disabled={actionKey !== null || departments.length === 0}
                        onChange={(event) => void changeDepartment(member, event.target.value)}
                        className={SELECT_CLASS}
                      >
                        {member.department_id === null ? <option value="">Not set</option> : null}
                        {member.department_id !== null && !assignedIsListed ? (
                          <option value={member.department_id}>
                            {member.department_name ?? 'Inactive department'}
                          </option>
                        ) : null}
                        {departments.map((department) => (
                          <option key={department.department_id} value={department.department_id}>
                            {department.name} ({department.code})
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-2 capitalize text-muted">{member.status}</td>
                    <td className="flex flex-wrap gap-2 p-2">
                      {appointment ? (
                        <button
                          type="button"
                          disabled={actionKey !== null}
                          onClick={() => void removeHod(member)}
                          className={BUTTON_CLASS}
                        >
                          {actionKey === `hod:${member.user_id}` ? 'Removing…' : 'Remove HOD'}
                        </button>
                      ) : canBeHead ? (
                        <button
                          type="button"
                          disabled={actionKey !== null || member.department_id === null}
                          title={member.department_id === null ? 'Set a department first' : undefined}
                          onClick={() => void makeHod(member)}
                          className={BUTTON_CLASS}
                        >
                          {actionKey === `hod:${member.user_id}` ? 'Appointing…' : 'Make HOD'}
                        </button>
                      ) : null}
                      {managePermissions && member.role === 'staff' && member.status === 'active' ? (
                        <button
                          type="button"
                          disabled={actionKey !== null}
                          onClick={() => managePermissions(member)}
                          className={BUTTON_CLASS}
                        >
                          Permissions
                        </button>
                      ) : null}
                      {member.user_id && member.status === 'active' ? (
                        <button
                          type="button"
                          disabled={actionKey !== null}
                          onClick={() => void lifecycle(member, 'deactivate')}
                          className={BUTTON_CLASS}
                        >
                          {actionKey === `deactivate:${member.user_id}` ? 'Deactivating…' : 'Deactivate'}
                        </button>
                      ) : null}
                      {member.user_id && (member.status === 'inactive' || member.status === 'deactivated') ? (
                        <button
                          type="button"
                          disabled={actionKey !== null}
                          onClick={() => void lifecycle(member, 'reactivate')}
                          className={BUTTON_CLASS}
                        >
                          {actionKey === `reactivate:${member.user_id}` ? 'Reactivating…' : 'Reactivate'}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

import { queryClient } from '../../../lib/queryClient.ts'
import { addDepartmentHead, endDepartmentHead } from '../../../services/students/transferApi.ts'
import type { Department } from '../../../types/academicSetup.ts'
import type { MembershipRosterEntry } from '../../../types/admin.ts'
import type { DepartmentHead } from '../../../types/transfer.ts'
import { staffFacultyKeys } from './staffFacultyKeys.ts'

export interface HeadAppointment {
  departmentId: string
  departmentName: string
  /** False when the department has since been deactivated. */
  departmentActive: boolean
}

interface Options {
  accessToken: string
  heads: DepartmentHead[]
  departments: Department[]
  runAction: (key: string, work: () => Promise<string>, failure: string) => Promise<void>
}

function listNames(names: string[]) {
  if (names.length <= 1) return names.join('')
  return `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`
}

/**
 * Head of Department from the Staff and Faculty roster. HOD is an appointment
 * on top of the Faculty role, not a role of its own. A faculty member may head
 * any number of active departments in the institution, and a department may
 * have several equal heads. The department-head endpoints enforce Faculty-only,
 * same institution and one appointment per person per department.
 */
export function useDepartmentHeadActions({ accessToken, heads, departments, runAction }: Options) {
  const departmentName = (id: string) =>
    departments.find((department) => department.department_id === id)?.name ?? 'an inactive department'

  function appointmentsOf(member: MembershipRosterEntry): HeadAppointment[] {
    return heads
      .filter((item) => item.faculty_user_id === member.user_id)
      .map((item) => ({
        departmentId: item.department_id,
        departmentName: departmentName(item.department_id),
        departmentActive: departments.some((department) => department.department_id === item.department_id),
      }))
      .sort((a, b) => a.departmentName.localeCompare(b.departmentName))
  }

  /** Names of the other current heads of a department. */
  function coHeadsOf(departmentId: string, exceptUserId: string) {
    return heads
      .filter((item) => item.department_id === departmentId && item.faculty_user_id !== exceptUserId)
      .map((item) => item.name)
  }

  function refreshOtherViews() {
    // Academic Setup's Head of Department panel caches the same data.
    void queryClient.invalidateQueries({ predicate: (query) => query.queryKey[2] === 'department-heads' })
  }

  /** Make the member head of exactly these departments, one appointment change at a time. */
  async function saveHodDepartments(member: MembershipRosterEntry, departmentIds: string[]) {
    const current = appointmentsOf(member).map((item) => item.departmentId)
    const toAdd = departmentIds.filter((id) => !current.includes(id))
    const toEnd = current.filter((id) => !departmentIds.includes(id))
    if (toAdd.length + toEnd.length === 0) return
    const name = member.name || member.email
    await runAction(
      `hod:${member.user_id}`,
      async () => {
        let done = 0
        try {
          for (const id of toEnd) {
            await endDepartmentHead(accessToken, id, member.user_id)
            done += 1
          }
          for (const id of toAdd) {
            await addDepartmentHead(accessToken, id, member.user_id)
            done += 1
          }
        } catch (cause) {
          // Earlier changes were saved; show them before reporting the failure.
          await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.heads(accessToken) })
          refreshOtherViews()
          const reason = cause instanceof Error ? cause.message : 'Could not update Head of Department.'
          throw new Error(done > 0 ? `Saved ${done} of ${toAdd.length + toEnd.length} changes. ${reason}` : reason)
        }
        refreshOtherViews()
        if (departmentIds.length === 0) return `${name} is no longer a Head of Department. They remain Faculty.`
        const names = departmentIds.map(departmentName).sort((a, b) => a.localeCompare(b))
        return `${name} is now Head of Department of ${listNames(names)}.`
      },
      'Could not update Head of Department.',
    )
  }

  return { appointmentsOf, coHeadsOf, saveHodDepartments }
}

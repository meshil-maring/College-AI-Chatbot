import { queryClient } from '../../../lib/queryClient.ts'
import { assignDepartmentHead } from '../../../services/students/transferApi.ts'
import type { Department } from '../../../types/academicSetup.ts'
import type { MembershipRosterEntry } from '../../../types/admin.ts'
import type { DepartmentHead } from '../../../types/transfer.ts'

export interface HeadAppointment {
  departmentId: string
  departmentName: string
}

interface Options {
  accessToken: string
  heads: DepartmentHead[]
  departments: Department[]
  runAction: (key: string, work: () => Promise<string>, failure: string) => Promise<void>
}

/**
 * Head of Department from the Staff and Faculty roster. HOD is an appointment
 * on top of the Faculty role, not a role of its own: "Make HOD" appoints a
 * Faculty member as head of the department they are assigned to. The existing
 * department-head endpoint enforces Faculty-only, same institution and one
 * head per department.
 */
export function useDepartmentHeadActions({ accessToken, heads, departments, runAction }: Options) {
  const departmentName = (id: string) =>
    departments.find((department) => department.department_id === id)?.name ?? 'a department'

  function headOf(member: MembershipRosterEntry): HeadAppointment | null {
    const head = heads.find((item) => item.faculty_user_id === member.user_id)
    return head ? { departmentId: head.department_id, departmentName: departmentName(head.department_id) } : null
  }

  function refreshOtherViews() {
    // Academic Setup's Head of Department panel caches the same data.
    void queryClient.invalidateQueries({ predicate: (query) => query.queryKey[2] === 'department-heads' })
  }

  async function makeHod(member: MembershipRosterEntry) {
    if (member.role !== 'faculty' || !member.department_id) return
    const departmentId = member.department_id
    const name = member.name || member.email
    const current = heads.find((item) => item.department_id === departmentId)
    const replaces = current && current.faculty_user_id !== member.user_id ? ` This replaces ${current.name}.` : ''
    if (!window.confirm(`Make ${name} Head of Department of ${departmentName(departmentId)}?${replaces}`)) return
    await runAction(
      `hod:${member.user_id}`,
      async () => {
        await assignDepartmentHead(accessToken, departmentId, member.user_id)
        refreshOtherViews()
        return `${name} is now Head of Department of ${departmentName(departmentId)}.`
      },
      'Could not appoint the Head of Department.',
    )
  }

  async function removeHod(member: MembershipRosterEntry) {
    const appointment = headOf(member)
    if (!appointment) return
    const name = member.name || member.email
    if (!window.confirm(`Remove ${name} as Head of Department of ${appointment.departmentName}?`)) return
    await runAction(
      `hod:${member.user_id}`,
      async () => {
        await assignDepartmentHead(accessToken, appointment.departmentId, null)
        refreshOtherViews()
        return `${name} is no longer Head of Department. They remain Faculty.`
      },
      'Could not remove the Head of Department.',
    )
  }

  return { headOf, makeHod, removeHod }
}

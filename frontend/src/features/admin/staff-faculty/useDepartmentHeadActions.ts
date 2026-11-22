import { queryClient } from '../../../lib/queryClient.ts'
import { addDepartmentHead, endDepartmentHead, setDepartmentHeadTerm } from '../../../services/students/transferApi.ts'
import type { Department } from '../../../types/academicSetup.ts'
import type { MembershipRosterEntry } from '../../../types/admin.ts'
import type { DepartmentHead, DepartmentHeadTerm } from '../../../types/transfer.ts'
import { staffFacultyKeys } from './staffFacultyKeys.ts'

export interface HeadAppointment extends DepartmentHeadTerm {
  departmentId: string
  departmentName: string
  /** False when the department has since been deactivated. */
  departmentActive: boolean
}

/** One department the member should head, with the appointment's term. */
export interface HeadSelection extends DepartmentHeadTerm {
  departmentId: string
}

interface Options {
  accessToken: string
  heads: DepartmentHead[]
  departments: Department[]
  /** Institution policy: may one faculty member head several departments? */
  allowMultiHod: boolean
  runAction: (key: string, work: () => Promise<string>, failure: string) => Promise<void>
}

function listNames(names: string[]) {
  if (names.length <= 1) return names.join('')
  return `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`
}

/**
 * Head of Department from the Staff and Faculty roster. HOD is a dated
 * responsibility on top of the Faculty role, not a role of its own. A
 * department may have several equal heads; whether one faculty member may head
 * several departments is the institution's policy. The department-head
 * endpoints enforce Faculty-only, same institution, the policy and the dates.
 */
export function useDepartmentHeadActions({ accessToken, heads, departments, allowMultiHod, runAction }: Options) {
  const departmentName = (id: string) =>
    departments.find((department) => department.department_id === id)?.name ?? 'an inactive department'

  function appointmentsOf(member: MembershipRosterEntry): HeadAppointment[] {
    return heads
      .filter((item) => item.faculty_user_id === member.user_id)
      .map((item) => ({
        departmentId: item.department_id,
        departmentName: departmentName(item.department_id),
        departmentActive: departments.some((department) => department.department_id === item.department_id),
        starts_on: item.starts_on,
        planned_end_on: item.planned_end_on ?? null,
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

  /**
   * Make the member head of exactly these departments with these terms: end
   * removed appointments, add new ones with their dates, and save changed dates.
   */
  async function saveHodDepartments(member: MembershipRosterEntry, selections: HeadSelection[]) {
    const current = appointmentsOf(member)
    const chosen = selections.map((item) => item.departmentId)
    const toEnd = current.filter((item) => !chosen.includes(item.departmentId)).map((item) => item.departmentId)
    const toAdd = selections.filter((item) => !current.some((existing) => existing.departmentId === item.departmentId))
    const toUpdate = selections.filter((item) =>
      current.some(
        (existing) =>
          existing.departmentId === item.departmentId &&
          (existing.starts_on !== item.starts_on ||
            (existing.planned_end_on ?? null) !== (item.planned_end_on ?? null)),
      ),
    )
    const total = toEnd.length + toAdd.length + toUpdate.length
    if (total === 0) return
    const name = member.name || member.email
    const term = ({ starts_on, planned_end_on }: HeadSelection) => ({
      starts_on,
      planned_end_on: planned_end_on || null,
    })
    await runAction(
      `hod:${member.user_id}`,
      async () => {
        let done = 0
        try {
          // End first, so a one-department policy allows moving to another department.
          for (const id of toEnd) {
            await endDepartmentHead(accessToken, id, member.user_id)
            done += 1
          }
          for (const item of toAdd) {
            await addDepartmentHead(accessToken, item.departmentId, member.user_id, term(item))
            done += 1
          }
          for (const item of toUpdate) {
            await setDepartmentHeadTerm(accessToken, item.departmentId, member.user_id, term(item))
            done += 1
          }
        } catch (cause) {
          // Earlier changes were saved; show them before reporting the failure.
          await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.heads(accessToken) })
          refreshOtherViews()
          const reason = cause instanceof Error ? cause.message : 'Could not update Head of Department.'
          throw new Error(done > 0 ? `Saved ${done} of ${total} changes. ${reason}` : reason)
        }
        refreshOtherViews()
        if (selections.length === 0) return `${name} is no longer a Head of Department. They remain Faculty.`
        const names = chosen.map(departmentName).sort((a, b) => a.localeCompare(b))
        return `${name} is now Head of Department of ${listNames(names)}.`
      },
      'Could not update Head of Department.',
    )
  }

  return { appointmentsOf, coHeadsOf, saveHodDepartments, allowMultiHod }
}

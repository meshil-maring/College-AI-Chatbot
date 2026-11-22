import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import {
  assignMemberResponsibility,
  endMemberResponsibility,
  listMemberResponsibilities,
} from '../../../../services/admin/adminApi.ts'
import { getAcademicSetup } from '../../../../services/admin/academics.ts'
import { getAcademicStructure } from '../../../../services/admin/academicStructure.ts'
import { setDepartmentHeadPolicy } from '../../../../services/students/transferApi.ts'
import type { MemberResponsibility, MemberResponsibilityAssign } from '../../../../types/admin/responsibilities.ts'
import { staffFacultyKeys } from '../staffFacultyKeys.ts'

export interface ResponsibilityTarget {
  id: string
  label: string
}

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

/** Active class sections and catalogue courses an appointment can be attached to. */
async function loadTargets(accessToken: string) {
  const [structure, catalogue] = await Promise.all([getAcademicStructure(accessToken), getAcademicSetup(accessToken)])
  const label = (item: { name: string; code: string }) => `${item.name} (${item.code})`
  const sort = (items: ResponsibilityTarget[]) => items.sort((a, b) => a.label.localeCompare(b.label))
  return {
    sections: sort(
      (structure.records.academic_sections ?? [])
        .filter((item) => item.is_active)
        .map((item) => ({ id: item.academic_section_id, label: label(item) })),
    ),
    courses: sort(
      (catalogue.records.courses ?? [])
        .filter((item) => item.is_active)
        .map((item) => ({ id: item.course_id, label: label(item) })),
    ),
  }
}

/**
 * Class In-Charge and Subject Coordinator appointments, the sections and
 * courses they can be attached to, and the institution's HOD policy command.
 * Results from an earlier session are ignored.
 */
export function useMemberResponsibilities(accessToken: string) {
  const list = useQuery(
    {
      queryKey: staffFacultyKeys.responsibilities(accessToken),
      queryFn: () => listMemberResponsibilities(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const targets = useQuery(
    {
      queryKey: staffFacultyKeys.responsibilityTargets(accessToken),
      queryFn: () => loadTargets(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const identity = useRef(accessToken)
  identity.current = accessToken

  useEffect(() => {
    setActionKey(null)
    setNotice(null)
    setError(null)
  }, [accessToken])

  /** Runs one command; returns an error message, or null when it succeeded. */
  async function run(key: string, work: () => Promise<string>, failure: string): Promise<string | null> {
    setActionKey(key)
    setNotice(null)
    setError(null)
    try {
      const text = await work()
      if (identity.current !== accessToken) return null
      setNotice(text)
      return null
    } catch (cause) {
      if (identity.current !== accessToken) return null
      const reason = message(cause, failure)
      setError(reason)
      return reason
    } finally {
      if (identity.current === accessToken) {
        await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.responsibilities(accessToken) })
        setActionKey(null)
      }
    }
  }

  const assign = (body: MemberResponsibilityAssign) =>
    run('assign', async () => (await assignMemberResponsibility(accessToken, body)).message, 'Could not assign.')

  const end = (item: MemberResponsibility) => {
    if (!window.confirm(`End ${item.faculty_name}'s appointment for ${item.target_name ?? 'this item'}?`)) {
      return Promise.resolve(null)
    }
    return run(
      `end:${item.responsibility_id}`,
      async () => (await endMemberResponsibility(accessToken, item.responsibility_id)).message,
      'Could not end the appointment.',
    )
  }

  const setPolicy = (allow: boolean) =>
    run(
      'policy',
      async () => {
        await setDepartmentHeadPolicy(accessToken, allow)
        await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.heads(accessToken) })
        return allow
          ? 'A faculty member can now head more than one department.'
          : 'New appointments are now limited to one department per Head. Existing appointments stay.'
      },
      'Could not change the policy.',
    )

  return {
    responsibilities: list.data?.responsibilities ?? [],
    sections: targets.data?.sections ?? [],
    courses: targets.data?.courses ?? [],
    loading: list.isPending,
    loadError: list.error ? message(list.error, 'Could not load responsibilities.') : null,
    targetsError: targets.error ? message(targets.error, 'Could not load class sections and courses.') : null,
    actionKey,
    notice,
    error,
    dismiss: () => {
      setNotice(null)
      setError(null)
    },
    assign,
    end,
    setPolicy,
  }
}

export type MemberResponsibilitiesModel = ReturnType<typeof useMemberResponsibilities>

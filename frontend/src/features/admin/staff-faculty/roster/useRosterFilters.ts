import { useMemo, useState } from 'react'
import type { MembershipRole, MembershipRosterEntry } from '../../../../types/admin.ts'

export type RoleFilter = 'all' | MembershipRole
export type StatusFilter = 'all' | 'active' | 'inactive'
/** 'all', 'none' (no department yet) or a department id. */
export type DepartmentFilter = string

export const NO_DEPARTMENT = 'none'

function isInactive(status: string) {
  return status === 'inactive' || status === 'deactivated'
}

/**
 * Client-side search and filters over the loaded roster. The roster is one
 * institution's Staff and Faculty, so filtering in the browser is instant and
 * needs no extra requests. Members are listed alphabetically.
 */
export function useRosterFilters(members: MembershipRosterEntry[]) {
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<RoleFilter>('all')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [department, setDepartment] = useState<DepartmentFilter>('all')

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return members
      .filter((member) => {
        if (role !== 'all' && member.role !== role) return false
        if (status === 'active' && member.status !== 'active') return false
        if (status === 'inactive' && !isInactive(member.status)) return false
        if (department === NO_DEPARTMENT && member.department_id !== null) return false
        if (department !== 'all' && department !== NO_DEPARTMENT && member.department_id !== department) return false
        if (!needle) return true
        return [member.name, member.email, member.department_name ?? '', member.department_code ?? '']
          .join(' ')
          .toLowerCase()
          .includes(needle)
      })
      .sort((a, b) => (a.name || a.email).localeCompare(b.name || b.email))
  }, [members, search, role, status, department])

  const filtered = search.trim() !== '' || role !== 'all' || status !== 'all' || department !== 'all'

  function clear() {
    setSearch('')
    setRole('all')
    setStatus('all')
    setDepartment('all')
  }

  return {
    search,
    setSearch,
    role,
    setRole,
    status,
    setStatus,
    department,
    setDepartment,
    visible,
    filtered,
    clear,
  }
}

export type RosterFilters = ReturnType<typeof useRosterFilters>

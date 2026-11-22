import { useMemo, useState } from 'react'
import type { DirectoryItem, UserType } from './directoryItems.ts'

export type RoleFilter = 'all' | UserType
/** 'inactive' covers deactivated (and older inactive) accounts; 'pending' is an open invitation. */
export type StatusFilter = 'all' | 'active' | 'pending' | 'suspended' | 'inactive'
/** 'all', 'none' (no department yet) or a department id. */
export type DepartmentFilter = string

export const NO_DEPARTMENT = 'none'

function matchesStatus(item: DirectoryItem, status: StatusFilter) {
  if (status === 'all') return true
  if (status === 'pending') return item.status === 'invited'
  if (status === 'inactive') return item.status === 'inactive' || item.status === 'deactivated'
  return item.status === status
}

/**
 * Client-side search and filters over the user directory: Staff, Faculty,
 * administrators and pending invitations of one institution. Filtering in the
 * browser is instant and needs no extra requests. Rows are alphabetical.
 */
export function useRosterFilters(items: DirectoryItem[]) {
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<RoleFilter>('all')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [department, setDepartment] = useState<DepartmentFilter>('all')
  const [employmentType, setEmploymentType] = useState('all')
  const [employmentStatus, setEmploymentStatus] = useState('all')

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return items
      .filter((item) => {
        if (role !== 'all' && item.userType !== role) return false
        if (!matchesStatus(item, status)) return false
        if (department === NO_DEPARTMENT && item.departmentId !== null) return false
        if (department !== 'all' && department !== NO_DEPARTMENT && item.departmentId !== department) return false
        if (employmentType !== 'all' && item.employmentType !== employmentType) return false
        if (employmentStatus !== 'all' && item.employmentStatus !== employmentStatus) return false
        if (!needle) return true
        return [
          item.name,
          item.email,
          item.departmentName ?? '',
          item.member?.department_code ?? '',
          item.employeeId ?? '',
          item.designation ?? '',
        ]
          .join(' ')
          .toLowerCase()
          .includes(needle)
      })
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [items, search, role, status, department, employmentType, employmentStatus])

  const filtered =
    search.trim() !== '' ||
    role !== 'all' ||
    status !== 'all' ||
    department !== 'all' ||
    employmentType !== 'all' ||
    employmentStatus !== 'all'

  function clear() {
    setSearch('')
    setRole('all')
    setStatus('all')
    setDepartment('all')
    setEmploymentType('all')
    setEmploymentStatus('all')
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
    employmentType,
    setEmploymentType,
    employmentStatus,
    setEmploymentStatus,
    visible,
    filtered,
    clear,
  }
}

export type RosterFilters = ReturnType<typeof useRosterFilters>

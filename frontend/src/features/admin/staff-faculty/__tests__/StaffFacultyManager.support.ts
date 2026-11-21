import { beforeEach, vi } from 'vitest'
import * as academics from '../../../../services/admin/academics.ts'
import * as api from '../../../../services/admin/adminApi.ts'
import * as transfers from '../../../../services/students/transferApi.ts'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'

// Import this module before StaffFacultyManager so both API modules are mocked.
vi.mock('../../../../services/admin/adminApi.ts')
vi.mock('../../../../services/admin/academics.ts', () => ({ getAcademicSetup: vi.fn() }))
vi.mock('../../../../services/students/transferApi.ts', () => ({
  getDepartmentHeads: vi.fn(),
  assignDepartmentHead: vi.fn(),
  addDepartmentHead: vi.fn(),
  endDepartmentHead: vi.fn(),
}))

export const request = {
  request_id: '10000000-0000-0000-0000-000000000001',
  full_name: 'Ada Faculty',
  email: 'ada@example.test',
  requested_role: 'faculty' as const,
  status: 'pending' as const,
  created_at: '2026-10-04T00:00:00Z',
}

export const CSE = {
  department_id: '60000000-0000-0000-0000-000000000001',
  institution_id: 'institution-1',
  name: 'Computer Science',
  code: 'CSE',
  is_active: true,
  description: null,
}

export const MECH = { ...CSE, department_id: '60000000-0000-0000-0000-000000000002', name: 'Mechanical', code: 'ME' }

export function member(changes: Partial<MembershipRosterEntry> = {}): MembershipRosterEntry {
  return {
    user_id: '20000000-0000-0000-0000-000000000001',
    name: 'Sam Staff',
    email: 'sam@example.test',
    role: 'staff',
    status: 'active',
    created_at: null,
    updated_at: null,
    department_id: null,
    department_code: null,
    department_name: null,
    ...changes,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  vi.mocked(api.listMembershipRequests).mockResolvedValue({ requests: [request], total: 1 })
  vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [], total: 0 })
  vi.mocked(api.listMembershipInvitations).mockResolvedValue({ invitations: [], total: 0 })
  vi.mocked(api.getDelegableStaffPermissions).mockResolvedValue(['documents.read'])
  vi.mocked(api.getStaffPermissions).mockResolvedValue({
    user_id: member().user_id,
    institution_id: 'institution-1',
    permissions: [],
    delegable_permissions: ['documents.read'],
  })
  vi.mocked(transfers.getDepartmentHeads).mockResolvedValue({ institution_id: 'institution-1', heads: [], faculty: [] })
  vi.mocked(academics.getAcademicSetup).mockResolvedValue({
    institution_id: 'institution-1',
    records: { departments: [MECH, CSE, { ...CSE, department_id: 'old', name: 'Closed', is_active: false }] },
    manageable: [],
  })
})

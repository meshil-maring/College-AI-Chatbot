import './__tests__/StaffFacultyManager.support.ts'
import { CSE, MECH, member } from './__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'
import * as transfers from '../../../services/students/transferApi.ts'

const teacher = member({ name: 'Tina Teacher', role: 'faculty', department_id: CSE.department_id })

function head(userId: string, name: string, departmentId = CSE.department_id) {
  return {
    department_id: departmentId,
    faculty_user_id: userId,
    name,
    email: null,
    assigned_at: '2026-11-21T00:00:00Z',
    is_active_faculty: true,
  }
}

function withHeads(heads: ReturnType<typeof head>[]) {
  vi.mocked(transfers.getDepartmentHeads).mockResolvedValue({ institution_id: 'institution-1', heads, faculty: [] })
}

describe('Staff and Faculty Management — Head of Department', () => {
  it('appoints a Faculty member as HOD of their own department', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    vi.mocked(transfers.assignDepartmentHead).mockResolvedValue({} as never)
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Make HOD' }))
    expect(window.confirm).toHaveBeenCalledWith('Make Tina Teacher Head of Department of Computer Science?')
    await waitFor(() =>
      expect(transfers.assignDepartmentHead).toHaveBeenCalledWith('jwt', CSE.department_id, teacher.user_id),
    )
    expect(await screen.findByText('Tina Teacher is now Head of Department of Computer Science.')).toBeInTheDocument()
  })

  it('warns when the appointment replaces the current HOD', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    withHeads([head('someone-else', 'Old Head')])
    vi.mocked(window.confirm).mockReturnValue(false)
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Make HOD' }))
    expect(window.confirm).toHaveBeenCalledWith(
      'Make Tina Teacher Head of Department of Computer Science? This replaces Old Head.',
    )
    expect(transfers.assignDepartmentHead).not.toHaveBeenCalled()
  })

  it('shows the HOD badge and removes the appointment', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    withHeads([head(teacher.user_id, 'Tina Teacher', MECH.department_id)])
    vi.mocked(transfers.assignDepartmentHead).mockResolvedValue({} as never)
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('HOD · Mechanical')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Make HOD' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Remove HOD' }))
    await waitFor(() => expect(transfers.assignDepartmentHead).toHaveBeenCalledWith('jwt', MECH.department_id, null))
    expect(await screen.findByText(/no longer Head of Department/)).toBeInTheDocument()
  })

  it('needs a department before a Faculty member can be made HOD', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [{ ...teacher, department_id: null }],
      total: 1,
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByRole('button', { name: 'Make HOD' })).toBeDisabled()
  })

  it('never offers HOD to Staff or inactive Faculty', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [member({ department_id: CSE.department_id }), { ...teacher, user_id: 't2', status: 'deactivated' }],
      total: 2,
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    await screen.findByText('Sam Staff')
    expect(screen.queryByRole('button', { name: 'Make HOD' })).toBeNull()
  })

  it('shows the server reason when an appointment is refused', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    vi.mocked(transfers.assignDepartmentHead).mockRejectedValue(new Error('Only active faculty can be appointed.'))
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Make HOD' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Only active faculty can be appointed.')
  })

  it('keeps the roster usable when HOD data cannot be loaded', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [teacher], total: 1 })
    vi.mocked(transfers.getDepartmentHeads).mockRejectedValue(new Error('down'))
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('Tina Teacher')).toBeInTheDocument()
    expect(screen.queryByText(/HOD ·/)).toBeNull()
  })
})

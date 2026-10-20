import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentManager, { loadStudentDirectory } from './StudentManager.tsx'
import * as api from '../../../services/adminApi.ts'
import type { Student } from '../../../types/admin.ts'

vi.mock('../../../services/adminApi.ts')
const auth = vi.hoisted(() => ({ accessToken: 'token', user: { institution_id: 'institution-a' as string | null, effective_permissions: ['*'] as string[] } }))
vi.mock('../../auth/AuthProvider.tsx', () => ({ useAuth: () => auth }))
const student = (number: string): Student => ({ student_id: number, student_number: number, user_id: 'hidden-user', institution_id: 'institution-a', program_id: null, academic_year_id: null, enrollment_date: '2026-10-01', expected_graduation_date: null, status: 'active', is_active: true, created_at: '', updated_at: '' })
const props = { section: 'all' as const, search: '', onSearch: vi.fn(), onSection: vi.fn() }
beforeEach(() => { vi.clearAllMocks(); auth.user.institution_id = 'institution-a'; auth.user.effective_permissions = ['*']; vi.mocked(api.listStudents).mockResolvedValue([student('REG001')]) })

describe('admin student workspace', () => {
  it('reads all pages using the authenticated institution before returning the directory', async () => {
    vi.mocked(api.listStudents).mockResolvedValueOnce(Array.from({ length: 100 }, (_, index) => student(`REG${index}`))).mockResolvedValueOnce([student('LAST')])
    expect(await loadStudentDirectory('token', 'institution-a')).toHaveLength(101)
    expect(api.listStudents).toHaveBeenNthCalledWith(1, 'token', 'institution-a', { limit: 100, offset: 0 })
    expect(api.listStudents).toHaveBeenNthCalledWith(2, 'token', 'institution-a', { limit: 100, offset: 100 })
  })
  it('renders live records and filters by student number without displaying internal identifiers', async () => {
    const view = render(<StudentManager {...props} />)
    expect(await screen.findByText('REG001')).toBeInTheDocument()
    expect(screen.queryByText('hidden-user')).not.toBeInTheDocument()
    view.rerender(<StudentManager {...props} search="missing" />)
    expect(screen.getByText('No matching students')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Bulk Import' }))
    expect(props.onSection).toHaveBeenCalledWith('import')
  })
  it('never requests a directory without institution context', () => {
    auth.user.institution_id = null
    render(<StudentManager {...props} />)
    expect(screen.getByRole('status')).toHaveTextContent('No institution is linked')
    expect(api.listStudents).not.toHaveBeenCalled()
  })
  it('shows retry on load failure and recovers without treating failure as an empty directory', async () => {
    vi.mocked(api.listStudents).mockRejectedValueOnce(new Error('Directory unavailable'))
    render(<StudentManager {...props} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Directory unavailable')
    expect(screen.queryByText('Your student directory starts here')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('REG001')).toBeInTheDocument()
  })
  it('does not request the approval queue without effective approval permissions', () => {
    auth.user.effective_permissions = ['students.read']
    render(<StudentManager {...props} section="requests" />)
    expect(screen.getByRole('status')).toHaveTextContent('does not have permission')
    expect(api.listPendingStudents).not.toHaveBeenCalled()
  })
})

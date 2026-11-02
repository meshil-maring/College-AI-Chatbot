import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentDirectoryPage from './StudentDirectoryPage.tsx'
import type { StudentDirectoryResponse } from '../../../../types/admin/students.ts'

const api = vi.hoisted(() => ({
  getStudentDirectory: vi.fn(),
  resendStudentInvitation: vi.fn(),
  updateStudentProfile: vi.fn(),
  setStudentActive: vi.fn(),
  deleteStudentProfile: vi.fn(),
}))
const structureApi = vi.hoisted(() => ({ getAcademicStructure: vi.fn() }))
vi.mock('../../../../services/admin/students.ts', () => api)
vi.mock('../../../../services/admin/academicStructure.ts', () => structureApi)

const result: StudentDirectoryResponse = {
  items: [
    {
      record_id: 'student-1',
      record_type: 'student',
      student_name: 'Ada Lovelace',
      email: 'ada@example.test',
      register_number: 'REG-1',
      university_roll_number: 'UNI-1',
      status: 'signed_in',
      approval_status: 'approved',
      account_status: 'active',
      student_status: 'active',
      is_active: true,
      last_sign_in_at: '2026-10-28T10:00:00Z',
      email_delivery_status: null,
      expires_at: null,
      program_id: 'program-1',
      program_name: 'Computer Science',
      program_code: 'CS',
      course_name: 'B.Tech',
      branch_name: 'Computer Science',
      branch_code: 'CS',
      batch_name: '2026–2030',
      batch_code: 'CS26',
      admission_cohort_id: 'cohort-1',
      section_name: 'Section A',
      section_code: 'A',
      academic_section_id: 'section-1',
      created_at: '2026-10-01T10:00:00Z',
    },
    {
      record_id: 'invitation-1',
      record_type: 'invitation',
      student_name: 'Grace Hopper',
      email: 'grace@example.test',
      register_number: 'REG-2',
      university_roll_number: null,
      status: 'pending_sign_in',
      approval_status: null,
      account_status: null,
      student_status: null,
      is_active: null,
      last_sign_in_at: null,
      email_delivery_status: 'sent',
      expires_at: '2099-01-01T00:00:00Z',
      program_id: 'program-1',
      program_name: 'Computer Science',
      program_code: 'CS',
      course_name: 'B.Tech',
      branch_name: 'Computer Science',
      branch_code: 'CS',
      batch_name: '2026–2030',
      batch_code: 'CS26',
      admission_cohort_id: 'cohort-1',
      section_name: 'Section A',
      section_code: 'A',
      academic_section_id: 'section-1',
      created_at: '2026-10-02T10:00:00Z',
    },
    {
      record_id: 'invitation-failed',
      record_type: 'invitation',
      student_name: 'Student With Failed Email',
      email: 'failed@example.test',
      register_number: 'REG-3',
      university_roll_number: null,
      status: 'pending_sign_in',
      approval_status: null,
      account_status: null,
      student_status: null,
      is_active: null,
      last_sign_in_at: null,
      email_delivery_status: 'failed',
      expires_at: '2099-01-01T00:00:00Z',
      program_id: 'program-1',
      program_name: 'Computer Science',
      program_code: 'CS',
      course_name: 'B.Tech',
      branch_name: 'Computer Science',
      branch_code: 'CS',
      batch_name: '2026–2030',
      batch_code: 'CS26',
      admission_cohort_id: 'cohort-1',
      section_name: 'Section A',
      section_code: 'A',
      academic_section_id: 'section-1',
      created_at: '2026-10-03T10:00:00Z',
    },
  ],
  total: 2,
  limit: 25,
  offset: 0,
  summary: { total: 2, pending_sign_in: 1, signed_in: 1, no_signin: 0 },
  programs: [{ program_id: 'program-1', program_name: 'Computer Science', program_code: 'CS' }],
}

function renderPage(
  permissions: {
    canUpdateStudents?: boolean
    canManageStudentPlacement?: boolean
    canDeleteStudents?: boolean
    canResendInvitations?: boolean
  } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <StudentDirectoryPage accessToken="token" identity="user:institution" {...permissions} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getStudentDirectory.mockResolvedValue(result)
  api.resendStudentInvitation.mockResolvedValue({
    delivery_message: 'Setup link sent to the student email.',
  })
  api.updateStudentProfile.mockResolvedValue({ student_id: 'student-1', updated: true })
  api.setStudentActive.mockImplementation((_token: string, studentId: string, active: boolean) =>
    Promise.resolve({ student_id: studentId, is_active: active }),
  )
  api.deleteStudentProfile.mockImplementation((_token: string, studentId: string) =>
    Promise.resolve({ student_id: studentId, deleted: true }),
  )
  structureApi.getAcademicStructure.mockResolvedValue({
    institution_id: 'institution',
    records: { academic_sections: [], admission_cohorts: [] },
    manageable: [],
    activities: [],
  })
})

describe('StudentDirectoryPage', () => {
  it('renders real records, academic placement, counts, and supported sign-in states', async () => {
    renderPage()

    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByText('Grace Hopper')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByText('B.Tech')).toHaveLength(3)
    expect(within(screen.getByRole('table')).getAllByText('Computer Science')).toHaveLength(3)
    expect(screen.getByRole('button', { name: 'Awaiting sign-in' })).toBeInTheDocument()
    expect(screen.getByRole('table')).toHaveTextContent('Signed in')
    expect(screen.queryByText('Phone number')).not.toBeInTheDocument()
    expect(api.getStudentDirectory).toHaveBeenCalledWith('token', {
      search: undefined,
      status: undefined,
      programId: undefined,
      limit: 25,
      offset: 0,
    })
  })

  it('applies status, program, and submitted search filters to the server query', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Ada Lovelace')

    await user.click(screen.getByRole('button', { name: 'Awaiting sign-in' }))
    await waitFor(() => {
      expect(api.getStudentDirectory).toHaveBeenLastCalledWith(
        'token',
        expect.objectContaining({
          status: 'pending_sign_in',
        }),
      )
    })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter by program' }), 'program-1')
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search students' }), { target: { value: 'Grace' } })
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))

    await waitFor(() => {
      expect(api.getStudentDirectory).toHaveBeenLastCalledWith('token', {
        search: 'Grace',
        status: 'pending_sign_in',
        programId: 'program-1',
        limit: 25,
        offset: 0,
      })
    })
  })

  it('shows a load error and retries the failed request', async () => {
    const user = userEvent.setup()
    api.getStudentDirectory.mockRejectedValueOnce(new Error('Directory is unavailable')).mockResolvedValueOnce(result)
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Directory is unavailable')
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(api.getStudentDirectory).toHaveBeenCalledTimes(2)
  })

  it('lets authorized administrators resend a failed setup link from All Students', async () => {
    const user = userEvent.setup()
    renderPage({ canResendInvitations: true })

    expect(await screen.findByText('Student With Failed Email')).toBeInTheDocument()
    expect(screen.getByText('Email failed — link not delivered')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Actions for Student With Failed Email' }))
    await user.click(screen.getByRole('button', { name: 'Resend setup link' }))

    expect(api.resendStudentInvitation).toHaveBeenCalledWith('token', 'invitation-failed')
    expect(await screen.findByText('Setup link sent to the student email.')).toBeInTheDocument()
  })

  it('does not expose resend actions without onboarding permissions', async () => {
    renderPage()

    expect(await screen.findByText('Student With Failed Email')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resend setup link' })).not.toBeInTheDocument()
  })
})

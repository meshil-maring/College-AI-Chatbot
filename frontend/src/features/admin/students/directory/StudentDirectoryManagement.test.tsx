import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentDirectoryPage from './StudentDirectoryPage.tsx'
import type { StudentDirectoryResponse } from '../../../../types/admin/students.ts'

const api = vi.hoisted(() => ({
  getStudentDirectory: vi.fn(),
  updateStudentProfile: vi.fn(),
  setStudentActive: vi.fn(),
  deleteStudentProfile: vi.fn(),
  resendStudentInvitation: vi.fn(),
  updateStudentInvitation: vi.fn(),
  cancelStudentInvitation: vi.fn(),
}))
vi.mock('../../../../services/admin/students.ts', () => api)
const structureApi = vi.hoisted(() => ({ getAcademicStructure: vi.fn() }))
vi.mock('../../../../services/admin/academicStructure.ts', () => structureApi)

const directory: StudentDirectoryResponse = {
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
      last_sign_in_at: null,
      email_delivery_status: null,
      expires_at: null,
      program_id: null,
      program_name: null,
      program_code: null,
      course_name: null,
      branch_name: null,
      branch_code: null,
      batch_name: null,
      batch_code: null,
      admission_cohort_id: null,
      section_name: null,
      section_code: null,
      academic_section_id: null,
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
      program_id: null,
      program_name: null,
      program_code: null,
      course_name: null,
      branch_name: null,
      branch_code: null,
      batch_name: '2026–2030',
      batch_code: 'CS26',
      admission_cohort_id: 'cohort-1',
      section_name: 'Section A',
      section_code: 'A',
      academic_section_id: 'section-1',
      created_at: '2026-10-02T10:00:00Z',
    },
  ],
  total: 2,
  limit: 25,
  offset: 0,
  summary: { total: 2, pending_sign_in: 1, signed_in: 1, no_signin: 0 },
  programs: [],
}

function renderPage(permissions: {
  canUpdateStudents?: boolean
  canManageStudentPlacement?: boolean
  canDeleteStudents?: boolean
}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <StudentDirectoryPage accessToken="token" identity="user:institution" {...permissions} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  directory.items[0].section_name = null
  api.getStudentDirectory.mockResolvedValue(directory)
  api.updateStudentProfile.mockResolvedValue({ student_id: 'student-1', updated: true })
  api.setStudentActive.mockResolvedValue({ student_id: 'student-1', is_active: false })
  api.deleteStudentProfile.mockResolvedValue({ student_id: 'student-1', deleted: true })
  api.updateStudentInvitation.mockResolvedValue({
    invitation: { invitation_id: 'invitation-1' },
    email_changed: false,
    delivery_status: null,
    delivery_message: null,
  })
  api.cancelStudentInvitation.mockResolvedValue({ invitation_id: 'invitation-1', cancelled: true })
  structureApi.getAcademicStructure.mockResolvedValue({
    institution_id: 'institution',
    records: { academic_sections: [], admission_cohorts: [] },
    manageable: [],
    activities: [],
  })
})

describe('StudentDirectoryPage management actions', () => {
  it('edits student identity details without changing the registered email', async () => {
    const user = userEvent.setup()
    renderPage({ canUpdateStudents: true, canManageStudentPlacement: true })

    await screen.findByText('Ada Lovelace')
    await user.click(screen.getByRole('button', { name: 'Actions for Ada Lovelace' }))
    await user.click(screen.getByRole('button', { name: 'Edit details' }))
    await user.clear(screen.getByLabelText('Student name'))
    await user.type(screen.getByLabelText('Student name'), 'Ada Byron Lovelace')
    await user.clear(screen.getByLabelText('Register number'))
    await user.type(screen.getByLabelText('Register number'), 'REG-NEW')
    expect(screen.getByLabelText(/Email/)).toHaveValue('ada@example.test')
    expect(screen.getByLabelText(/Email/)).toHaveAttribute('readonly')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => {
      expect(api.updateStudentProfile).toHaveBeenCalledWith('token', 'student-1', {
        student_name: 'Ada Byron Lovelace',
        register_number: 'REG-NEW',
        university_roll_number: 'UNI-1',
        academic_section_id: null,
      })
    })
    expect(await screen.findByText('Student details updated.')).toBeInTheDocument()
  })

  it('keeps placement read-only while the directory response lacks placement identifiers', async () => {
    const user = userEvent.setup()
    directory.items[0].section_name = 'Section A'
    renderPage({ canUpdateStudents: true, canManageStudentPlacement: true })

    await screen.findByText('Ada Lovelace')
    await user.click(screen.getByRole('button', { name: 'Actions for Ada Lovelace' }))
    await user.click(screen.getByRole('button', { name: 'Edit details' }))

    expect(screen.getByRole('dialog').querySelector('select')).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent('Apply the latest student directory migration')
  })

  it('requires confirmation before deactivating a student account', async () => {
    const user = userEvent.setup()
    renderPage({ canUpdateStudents: true })

    await screen.findByText('Ada Lovelace')
    await user.click(screen.getByRole('button', { name: 'Actions for Ada Lovelace' }))
    await user.click(screen.getByRole('button', { name: 'Deactivate' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('Academic and account history will be retained')
    await user.click(screen.getByRole('button', { name: 'Deactivate student' }))

    await waitFor(() => expect(api.setStudentActive).toHaveBeenCalledWith('token', 'student-1', false))
    expect(await screen.findByText('Student deactivated.')).toBeInTheDocument()
  })

  it('explains why a student with linked records cannot be deleted', async () => {
    const user = userEvent.setup()
    api.deleteStudentProfile.mockRejectedValue(new Error('Student has linked records and cannot be deleted.'))
    renderPage({ canDeleteStudents: true })

    await screen.findByText('Ada Lovelace')
    await user.click(screen.getByRole('button', { name: 'Actions for Ada Lovelace' }))
    await user.click(screen.getByRole('button', { name: 'Delete profile' }))
    await user.click(screen.getByRole('button', { name: 'Delete profile' }))

    expect(await screen.findByRole('dialog')).toHaveTextContent('Student has linked records and cannot be deleted.')
  })

  it('deletes a student profile after confirmation when the server permits it', async () => {
    const user = userEvent.setup()
    renderPage({ canDeleteStudents: true })

    await screen.findByText('Ada Lovelace')
    await user.click(screen.getByRole('button', { name: 'Actions for Ada Lovelace' }))
    await user.click(screen.getByRole('button', { name: 'Delete profile' }))
    await user.click(screen.getByRole('button', { name: 'Delete profile' }))

    await waitFor(() => expect(api.deleteStudentProfile).toHaveBeenCalledWith('token', 'student-1'))
    expect(await screen.findByText('Student profile deleted.')).toBeInTheDocument()
  })

  it('lets an admin correct a pending invitation email and sends a fresh setup link', async () => {
    const user = userEvent.setup()
    renderPage({ canUpdateStudents: true })

    await screen.findByText('Grace Hopper')
    await user.click(screen.getByRole('button', { name: 'Actions for Grace Hopper' }))
    await user.click(screen.getByRole('button', { name: 'Edit invitation' }))
    await user.clear(screen.getByLabelText('Student name'))
    await user.type(screen.getByLabelText('Student name'), 'Grace Brewster Hopper')
    const email = screen.getByLabelText(/Email/)
    expect(email).not.toHaveAttribute('readonly')
    await user.clear(email)
    await user.type(email, 'grace.corrected@example.test')
    api.updateStudentInvitation.mockResolvedValue({
      invitation: { invitation_id: 'invitation-1' },
      email_changed: true,
      delivery_status: 'sent',
      delivery_message: 'Setup link sent to the corrected email.',
    })
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => {
      expect(api.updateStudentInvitation).toHaveBeenCalledWith('token', 'invitation-1', {
        email: 'grace.corrected@example.test',
        student_name: 'Grace Brewster Hopper',
        register_number: 'REG-2',
        university_roll_number: null,
        academic_section_id: null,
      })
    })
    expect(await screen.findByText('Setup link sent to the corrected email.')).toBeInTheDocument()
  })

  it('cancels a pending invitation after confirmation', async () => {
    const user = userEvent.setup()
    renderPage({ canDeleteStudents: true })

    await screen.findByText('Grace Hopper')
    await user.click(screen.getByRole('button', { name: 'Actions for Grace Hopper' }))
    await user.click(screen.getByRole('button', { name: 'Cancel invitation' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('The setup link will stop working')
    await user.click(screen.getByRole('button', { name: 'Cancel invitation' }))

    await waitFor(() => expect(api.cancelStudentInvitation).toHaveBeenCalledWith('token', 'invitation-1'))
    expect(await screen.findByText('Student invitation cancelled.')).toBeInTheDocument()
  })
})

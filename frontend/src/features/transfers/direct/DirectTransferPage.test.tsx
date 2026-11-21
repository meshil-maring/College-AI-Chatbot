import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { queryClient } from '../../../lib/queryClient.ts'
import * as api from '../../../services/students/transferApi.ts'
import type { DirectTransferOptions, DirectTransferStudents } from '../../../types/transfer.ts'
import DirectTransferPage from './DirectTransferPage.tsx'
import { currentFixture, optionFixture, sectionFixture } from '../__tests__/transferFixture.ts'

const auth = vi.hoisted(() => ({
  accessToken: 'token-1',
  role: 'admin',
  sessionGeneration: 1,
  user: { user_id: 'user-1', institution_id: 'tenant-1', effective_permissions: [] as string[] },
}))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../services/students/transferApi.ts')

function studentsFixture(overrides: Partial<DirectTransferStudents> = {}): DirectTransferStudents {
  return {
    institution_id: 'tenant-1',
    can_transfer: true,
    actor_role: 'admin',
    students: [
      {
        student_id: 'student-1',
        student_name: 'Asha Rao',
        register_number: 'REG-001',
        current_section: sectionFixture(),
        registration_status: 'registered',
        has_open_request: false,
      },
      {
        student_id: 'student-2',
        student_name: 'Ravi Kumar',
        register_number: 'REG-002',
        current_section: sectionFixture({ section_name: 'C' }),
        registration_status: 'assigned',
        has_open_request: true,
      },
    ],
    ...overrides,
  }
}

function optionsFixture(overrides: Partial<DirectTransferOptions> = {}): DirectTransferOptions {
  return {
    institution_id: 'tenant-1',
    student_id: 'student-1',
    actor_role: 'admin',
    current: currentFixture(),
    has_open_request: false,
    options: [optionFixture()],
    ...overrides,
  }
}

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  vi.mocked(api.getDirectTransferStudents).mockResolvedValue(studentsFixture())
  vi.mocked(api.getDirectTransferOptions).mockResolvedValue(optionsFixture())
})
afterEach(() => queryClient.clear())

it('transfers the chosen student immediately with a reason', async () => {
  vi.mocked(api.directTransfer).mockResolvedValue({
    transfer_request_id: 'request-9',
    institution_id: 'tenant-1',
    student_id: 'student-1',
    status: 'approved',
  })
  render(<DirectTransferPage />)
  fireEvent.change(await screen.findByRole('searchbox'), { target: { value: 'reg-001' } })
  expect(screen.queryByText(/Ravi Kumar/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /Asha Rao/ }))
  fireEvent.click(await screen.findByRole('radio', { name: /Section B/ }))
  fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: '  Balancing section sizes  ' } })
  const submit = screen.getByRole('button', { name: 'Transfer student' })
  expect(submit).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox', { name: /register again/ }))
  fireEvent.click(submit)
  await waitFor(() =>
    expect(api.directTransfer).toHaveBeenCalledExactlyOnceWith('token-1', {
      student_id: 'student-1',
      to_section_id: 'section-b',
      reason: 'Balancing section sizes',
    }),
  )
  expect(await screen.findByText(/Asha Rao was moved to/)).toBeInTheDocument()
})

it('sends a student with an open request back to Transfer Requests', async () => {
  vi.mocked(api.getDirectTransferOptions).mockResolvedValue(
    optionsFixture({ student_id: 'student-2', has_open_request: true }),
  )
  render(<DirectTransferPage />)
  fireEvent.click(await screen.findByRole('button', { name: /Ravi Kumar/ }))
  expect(await screen.findByText(/has an open transfer request/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Transfer student' })).not.toBeInTheDocument()
})

it('explains the department limit to an HOD and refuses non-reviewers', async () => {
  auth.role = 'faculty'
  vi.mocked(api.getDirectTransferStudents).mockResolvedValue(studentsFixture({ actor_role: 'hod' }))
  const { unmount } = render(<DirectTransferPage />)
  expect(await screen.findByText(/As Head of Department/)).toBeInTheDocument()
  unmount()
  queryClient.clear()
  vi.mocked(api.getDirectTransferStudents).mockResolvedValue(
    studentsFixture({ can_transfer: false, actor_role: null, students: [] }),
  )
  render(<DirectTransferPage />)
  expect(await screen.findByText(/Only administrators and current Heads of Department/)).toBeInTheDocument()
  auth.role = 'admin'
})

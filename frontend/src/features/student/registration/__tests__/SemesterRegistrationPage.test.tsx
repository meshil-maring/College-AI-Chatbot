import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { queryClient } from '../../../../lib/queryClient.ts'
import * as api from '../../../../services/academics/semesterRegistration.ts'
import SemesterRegistrationPage from '../SemesterRegistrationPage.tsx'
import { semesterFixture } from './registrationFixture.ts'

const auth = vi.hoisted(() => ({
  accessToken: 'token-1',
  role: 'student',
  sessionGeneration: 1,
  user: {
    user_id: 'user-1',
    institution_id: 'tenant-1',
    effective_permissions: ['registration.own.read', 'registration.own.manage'],
  },
}))
vi.mock('../../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../../services/academics/semesterRegistration.ts')

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  auth.user.user_id = 'user-1'
  auth.user.institution_id = 'tenant-1'
  auth.sessionGeneration = 1
  auth.accessToken = 'token-1'
  vi.mocked(api.getMySemesters).mockResolvedValue({ institution_id: 'tenant-1', items: [semesterFixture()] })
})
afterEach(() => queryClient.clear())

it('shows assignment guidance when no academic section has been assigned', async () => {
  vi.mocked(api.getMySemesters).mockResolvedValue({ institution_id: 'tenant-1', items: [] })
  render(<SemesterRegistrationPage />)
  expect(await screen.findByText(/No semester has been assigned yet/)).toBeInTheDocument()
})

it('discards old choices and ignores a late completion after identity replacement', async () => {
  let finish!: (value: Awaited<ReturnType<typeof api.completeMySemester>>) => void
  vi.mocked(api.completeMySemester).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  const page = render(<SemesterRegistrationPage />)
  fireEvent.click(await screen.findByRole('radio', { name: /Option 2/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Register selected subjects' }))
  await waitFor(() => expect(api.completeMySemester).toHaveBeenCalledOnce())
  auth.user.user_id = 'user-2'
  auth.user.institution_id = 'tenant-2'
  auth.accessToken = 'token-2'
  auth.sessionGeneration = 2
  vi.mocked(api.getMySemesters).mockResolvedValue({ institution_id: 'tenant-2', items: [] })
  page.rerender(<SemesterRegistrationPage />)
  await screen.findByText(/No semester has been assigned yet/)
  await act(async () => {
    finish({ ...semesterFixture(), status: 'registered' })
  })
  expect(screen.queryByText('Registration complete')).not.toBeInTheDocument()
  expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  expect(api.getMySemesters).toHaveBeenCalledTimes(2)
})

it('rejects a response from another institution', async () => {
  vi.mocked(api.getMySemesters).mockResolvedValue({ institution_id: 'other-tenant', items: [semesterFixture()] })
  render(<SemesterRegistrationPage />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Registration data is unavailable for this institution.')
  expect(screen.queryByRole('radio')).not.toBeInTheDocument()
})

it('preserves the selected option on token renewal and submits with the new token', async () => {
  vi.mocked(api.completeMySemester).mockResolvedValue({ ...semesterFixture(), status: 'registered' })
  const page = render(<SemesterRegistrationPage />)
  fireEvent.click(await screen.findByRole('radio', { name: /Option 2/ }))
  auth.accessToken = 'renewed-token'
  page.rerender(<SemesterRegistrationPage />)
  expect(screen.getByRole('radio', { name: /Option 2/ })).toBeChecked()
  fireEvent.click(screen.getByRole('button', { name: 'Register selected subjects' }))
  await waitFor(() =>
    expect(api.completeMySemester).toHaveBeenCalledExactlyOnceWith('renewed-token', 'registration-1', ['option-2']),
  )
})

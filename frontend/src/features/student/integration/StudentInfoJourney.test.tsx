import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { goTo } from './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { getMyProfile, getMyNotices } from '../../../services/students/studentApi.ts'
import StudentShell from '../workspace/StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'

it('retries an information request without reloading account identity', async () => {
  mockAllLoaded()
  vi.mocked(getMyNotices).mockRejectedValueOnce(new Error('offline'))
  render(<StudentShell />)
  await screen.findByText('Welcome, REG-100')
  const user = userEvent.setup()
  await goTo(user, 'Notices')
  await screen.findByRole('alert')
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
  expect(getMyNotices).toHaveBeenCalledTimes(2)
  expect(getMyProfile).toHaveBeenCalledTimes(1)
})

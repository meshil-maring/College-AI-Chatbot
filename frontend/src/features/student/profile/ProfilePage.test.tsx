import '../integration/__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { getMyProfile } from '../../../services/students/studentApi.ts'
import { PROFILE } from '../__tests__/studentTestFixtures.ts'
import { ProfilePage } from './ProfilePage.tsx'

it('renders only approved identity fields and remains read only', async () => {
  vi.mocked(getMyProfile).mockResolvedValue({
    ...PROFILE,
    student_id: 'private-student-id',
    program_name: 'retired-program',
  } as typeof PROFILE)
  const { container } = render(<ProfilePage />)
  expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
  for (const value of ['student@college.edu', 'REG-100', 'ROLL-100', 'STU100', 'Test College', 'TC01']) {
    expect(screen.getByText(value)).toBeInTheDocument()
  }
  expect(screen.queryByText('private-student-id')).not.toBeInTheDocument()
  expect(screen.queryByText('retired-program')).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Academic context' })).not.toBeInTheDocument()
  expect(container.querySelectorAll('input, select, textarea, button')).toHaveLength(0)
})
it('retries an identity load using the profile endpoint', async () => {
  vi.mocked(getMyProfile).mockRejectedValueOnce(new Error('offline')).mockResolvedValue(PROFILE)
  render(<ProfilePage />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load your profile.')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
  expect(getMyProfile).toHaveBeenCalledTimes(2)
})

import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import StudentShell from '../workspace/StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'

it('moves active state using keyboard navigation without duplicate or academic entries', async () => {
  mockAllLoaded()
  render(<StudentShell />)
  const navigation = await screen.findByRole('navigation', { name: 'Student navigation' })
  const profile = within(navigation).getByRole('button', { name: 'Profile' })
  expect(profile).toHaveAttribute('aria-current', 'page')
  const notices = within(navigation).getByRole('button', { name: 'Notices' })
  notices.focus()
  await userEvent.keyboard('{Enter}')
  expect(await screen.findByRole('heading', { name: 'Notices', level: 1 })).toBeInTheDocument()
  expect(notices).toHaveAttribute('aria-current', 'page')
  expect(profile).not.toHaveAttribute('aria-current')
  expect(
    within(navigation)
      .getAllByRole('button')
      .map((item) => item.textContent),
  ).toEqual(['Profile', 'Notices', 'Learning Resources', 'AI Assistant'])
})

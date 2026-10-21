import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import StudentShell from '../workspace/StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'
describe('phase 6.16.4 navigation accessibility integration', () => {
  it('active state moves, navigation stays unique, and keyboard activation works', async () => {
    const user = userEvent.setup({ delay: null })
    mockAllLoaded()
    render(<StudentShell />)
    const navElement = await screen.findByRole('navigation', { name: 'Student navigation' })
    // One meaningful page heading per view; active nav state tracks it.
    expect(within(navElement).getByRole('button', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(within(navElement).getByRole('button', { name: 'Attendance' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()

    // Keyboard-only activation: focus the Attendance nav item, press Enter.
    const attendanceButton = within(navElement).getByRole('button', { name: 'Attendance' })
    attendanceButton.focus()
    expect(attendanceButton).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('heading', { level: 1, name: 'Attendance' })).toBeInTheDocument()
    expect(within(navElement).getByRole('button', { name: 'Attendance' })).toHaveAttribute('aria-current', 'page')
    expect(within(navElement).getByRole('button', { name: 'Dashboard' })).not.toHaveAttribute('aria-current')

    // No duplicate navigation entries and no privileged entries.
    const navLabels = within(navElement)
      .getAllByRole('button')
      .map((button) => button.textContent)
    expect(new Set(navLabels).size).toBe(navLabels.length)
    expect(navLabels).toEqual([
      'Dashboard',
      'Attendance',
      'Results',
      'Notices',
      'Learning Resources',
      'AI Assistant',
      'Profile',
    ])
  })
})

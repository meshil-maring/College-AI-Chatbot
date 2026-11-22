import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { goTo, logoutMock, openProfile } from './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { getMyProfile, getMyNotices, getMyResources } from '../../../services/students/studentApi.ts'
import StudentShell from '../workspace/StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'

describe('student identity and information journey', () => {
  it('opens profile, notices, resources and chat, then signs out', async () => {
    mockAllLoaded()
    const user = userEvent.setup()
    render(<StudentShell />)
    // The dashboard previews three notices; resources load only on their page.
    await openProfile(user)
    expect(getMyNotices).toHaveBeenCalledWith('test-token', 3)
    expect(getMyResources).not.toHaveBeenCalled()
    await goTo(user, 'Notices')
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    await goTo(user, 'Learning Resources')
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
    await goTo(user, 'Profile')
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(getMyProfile).toHaveBeenCalledTimes(1)
    await goTo(user, 'AI Assistant')
    expect(await screen.findByTestId('chat-shell-mock')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(logoutMock).toHaveBeenCalledOnce()
  })
  it('does not revive an academic view from an old URL', async () => {
    window.history.replaceState({}, '', '/student/attendance')
    mockAllLoaded()
    render(<StudentShell />)
    expect(
      await screen.findByRole('heading', { name: /^Good (morning|afternoon|evening)/, level: 1 }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Attendance' })).not.toBeInTheDocument()
    window.history.replaceState({}, '', '/')
  })
})

import './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { goTo, holder, logoutMock } from './__tests__/StudentExperienceFinalIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { getMyNotices, getMyResources } from '../../../services/students/studentApi.ts'
import StudentShell from '../workspace/StudentShell.tsx'
import { mockAllLoaded } from '../__tests__/studentTestFixtures.ts'

describe('institution information errors remain isolated', () => {
  it('keeps profile and resources usable after a notices failure', async () => {
    mockAllLoaded()
    vi.mocked(getMyNotices).mockRejectedValueOnce(new holder.actual.StudentApiError(500, 'private server details'))
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    const user = userEvent.setup()
    await goTo(user, 'Notices')
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load notices.')
    expect(screen.queryByText('private server details')).not.toBeInTheDocument()
    await goTo(user, 'Profile')
    expect(screen.getByText('Welcome, REG-100')).toBeInTheDocument()
    await goTo(user, 'Learning Resources')
    expect(await screen.findByText('Lecture notes week 3')).toBeInTheDocument()
    expect(logoutMock).not.toHaveBeenCalled()
    expect(getMyResources).toHaveBeenCalledTimes(1)
  })
  it('allows leaving an information page while its request remains pending', async () => {
    mockAllLoaded()
    vi.mocked(getMyNotices).mockReturnValue(new Promise(() => {}))
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    const user = userEvent.setup()
    await goTo(user, 'Notices')
    expect(screen.getByRole('status')).toBeInTheDocument()
    await goTo(user, 'Profile')
    expect(screen.getByText('Welcome, REG-100')).toBeInTheDocument()
  })
})

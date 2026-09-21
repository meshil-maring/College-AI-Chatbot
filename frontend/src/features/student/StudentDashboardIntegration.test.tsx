/** Phase 6.16.1 — dashboard integration: full journey and partial failure. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StudentApiError } from '../../services/studentApi.ts'
import { getMyResultsSummary } from '../../services/studentApi.ts'
import { getMyTestResultsSummary } from '../../services/studentApi.ts'
import { mockAllLoaded } from './studentTestFixtures.ts'

vi.mock('../chat/ChatShell.tsx', () => ({
  default: () => <div data-testid="chat-shell-mock">AI chat</div>,
}))
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' }, role: 'student',
    accessToken: 'test-token', logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status = 0; code: string | null = null;
  },
  getMyAcademicProfile: vi.fn(), getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(), getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(), getMyResources: vi.fn(),
}))

import StudentShell from './StudentShell.tsx'

beforeEach(() => { vi.clearAllMocks() })

describe('phase 6.16.1 dashboard integration', () => {
  it('full journey: identity through resources to assistant', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    render(<StudentShell />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('Midterm 1')).toBeInTheDocument()
    expect(screen.getByText('Exam schedule update')).toBeInTheDocument()
    expect(screen.getByText('Lecture notes week 3')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open AI Assistant' }))
    expect(await screen.findByTestId('chat-shell-mock')).toBeInTheDocument()
  })

  it('one failing section keeps the dashboard usable', async () => {
    mockAllLoaded()
    vi.mocked(getMyResultsSummary).mockRejectedValueOnce(new StudentApiError(500, 'x'))
    vi.mocked(getMyTestResultsSummary).mockRejectedValueOnce(new StudentApiError(500, 'x'))
    render(<StudentShell />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    const alerts = await screen.findAllByRole('alert')
    expect(within(alerts[0]).getByText('Unable to load results.')).toBeInTheDocument()
  })
})
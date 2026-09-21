/** Phase 6.16 — shell navigation/interaction tests. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StudentShell from './StudentShell.tsx'
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
beforeEach(() => { vi.clearAllMocks() })

describe('student shell navigation and interaction', () => {
  it('exposes seven student surfaces and no admin controls', async () => {
    mockAllLoaded()
    render(<StudentShell />)
    const nav = await screen.findByRole('navigation', { name: 'Student navigation' })
    for (const label of ['Dashboard', 'Attendance', 'Results', 'Notices', 'Learning Resources', 'AI Assistant', 'Profile']) {
      expect(within(nav).getByRole('button', { name: label })).toBeInTheDocument()
    }
    const navText = nav.textContent ?? ''
    for (const forbidden of ['Admin', 'Staff Management', 'Student Management', 'Role Management', 'Institution Management']) {
      expect(navText).not.toContain(forbidden)
    }
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('dashboard ViewLink navigates to attendance page', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    await user.click(screen.getByRole('button', { name: 'View all attendance' }))
    expect(await screen.findByRole('heading', { name: 'Attendance' })).toBeInTheDocument()
  })

  it('dashboard entry point opens the reused AI assistant', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    await user.click(screen.getByRole('button', { name: 'Open AI Assistant' }))
    expect(await screen.findByTestId('chat-shell-mock')).toBeInTheDocument()
  })

  it('top navigation reaches results, notices, and profile', async () => {
    const user = userEvent.setup()
    mockAllLoaded()
    render(<StudentShell />)
    await screen.findByText('Welcome, REG-100')
    const nav = screen.getByRole('navigation', { name: 'Student navigation' })
    await user.click(within(nav).getByRole('button', { name: 'Results' }))
    expect(await screen.findByText('Midterm 1')).toBeInTheDocument()
    await user.click(within(nav).getByRole('button', { name: 'Notices' }))
    expect(await screen.findByText('Exam schedule update')).toBeInTheDocument()
    await user.click(within(nav).getByRole('button', { name: 'Profile' }))
    expect(await screen.findByText('Test College (TC01)')).toBeInTheDocument()
  })
})

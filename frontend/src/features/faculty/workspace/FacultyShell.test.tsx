/**
 * Phase 6.17 — Faculty shell tests.
 *
 * The shell is selected from the server-authoritative /auth/me role; these
 * tests verify the faculty navigation, active state, assistant entry, and
 * that no admin surface is ever rendered for the faculty role.
 */

/// <reference types="vitest/globals" />
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FacultyShell from './FacultyShell.tsx'
import type { CurrentUser } from '../../../types/auth.ts'

const authState = vi.hoisted(() => ({
  status: 'authenticated' as string,
  user: null as CurrentUser | null,
  role: null as string | null,
  accessToken: 'test-token' as string | null,
  error: null as string | null,
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

const chatShellSpy = vi.hoisted(() => vi.fn())
const facultyAttendanceApi = vi.hoisted(() => ({
  commitFacultyAttendanceImport: vi.fn(),
  getFacultyAttendanceAssignments: vi.fn(),
  getFacultyAttendanceRoster: vi.fn(),
  markFacultyAttendance: vi.fn(),
  uploadFacultyAttendance: vi.fn(),
}))
vi.mock('../../chat/ChatShell.tsx', () => ({
  default: function ChatShellMock() {
    chatShellSpy('ChatShell rendered')
    return <div>ChatShellMock</div>
  },
}))
vi.mock('../../../services/faculty/facultyAttendanceApi.ts', () => facultyAttendanceApi)
vi.mock('../../../services/faculty/facultyTestsApi.ts', async (importOriginal) => ({
  ...await importOriginal<typeof import('../../../services/faculty/facultyTestsApi.ts')>(),
  getTestResources: vi.fn().mockResolvedValue([]),
  getTestTypes: vi.fn().mockResolvedValue([]),
}))

const FACULTY_USER: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  email: 'faculty@college.edu',
  role: 'faculty',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

beforeEach(() => {
  authState.status = 'authenticated'
  authState.user = FACULTY_USER
  authState.role = 'faculty'
  authState.accessToken = 'test-token'
  authState.error = null
  authState.logout.mockReset()
  chatShellSpy.mockClear()
})

afterEach(() => {
  // The fetch-absence test stubs the global; never leak it to other tests.
  vi.unstubAllGlobals()
})

describe('FacultyShell', () => {
  it('hides both student entries when the server grants no roster access', () => {
    authState.user = { ...FACULTY_USER, effective_permissions: ['profile.own.read'] }
    render(<FacultyShell />)
    expect(screen.queryByRole('button', { name: 'Students', exact: true })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'My Students', exact: true })).not.toBeInTheDocument()
  })
  it('opens the live Students directory from the faculty navigation', async () => {
    facultyAttendanceApi.getFacultyAttendanceAssignments.mockResolvedValue([])
    const user = userEvent.setup()
    render(<FacultyShell />)
    await user.click(screen.getByRole('button', { name: 'Students', exact: true }))
    expect(await screen.findByRole('heading', { name: 'No student rosters available' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/faculty/students')
    expect(screen.queryByText('No information is available for this section yet.')).not.toBeInTheDocument()
  })
  it('restores a faculty view directly from its URL', async () => {
    window.history.replaceState(null, '', '/faculty/students')
    facultyAttendanceApi.getFacultyAttendanceAssignments.mockResolvedValue([])
    render(<FacultyShell />)
    expect(await screen.findByRole('heading', { name: 'Students', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Students', exact: true })).toHaveAttribute('aria-current', 'page')
  })
  it('places student pages in a collapsible sidebar menu without page tabs', async () => {
    window.history.replaceState(null, '', '/faculty/students/record-history?section_id=section-1')
    facultyAttendanceApi.getFacultyAttendanceAssignments.mockResolvedValue([])
    const user = userEvent.setup()
    render(<FacultyShell />)
    await screen.findByRole('heading', { name: 'Section unavailable' })
    const students = screen.getByRole('button', { name: 'Students', exact: true })
    const sidebar = screen.getByRole('navigation', { name: 'Faculty navigation' })
    const pages = within(sidebar).getByRole('navigation', { name: 'Students pages' })
    expect(students).toHaveAttribute('aria-expanded', 'true')
    expect(within(pages).getByRole('link', { name: 'Record history' })).toHaveAttribute('aria-current', 'page')
    expect(within(pages).getByRole('link', { name: 'Waiting approval' })).toHaveAttribute('href', '/faculty/students/waiting-approval?section_id=section-1')
    expect(within(pages).getByText('Register')).toHaveAttribute('aria-disabled', 'true')
    expect(within(screen.getByRole('main')).queryByRole('navigation', { name: 'Students pages' })).not.toBeInTheDocument()
    await user.click(students)
    expect(students).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: 'Students pages' })).not.toBeInTheDocument()
    expect(window.location.pathname).toBe('/faculty/students/record-history')
    await user.click(students)
    expect(students).toHaveAttribute('aria-expanded', 'true')
    await user.click(screen.getByRole('link', { name: 'Waiting approval' }))
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/waiting-approval?section_id=section-1')
    expect(screen.getByRole('link', { name: 'Waiting approval' })).toHaveAttribute('aria-current', 'page')
  })
  it('keeps mobile navigation open while expanding Students and closes it after choosing a page', async () => {
    facultyAttendanceApi.getFacultyAttendanceAssignments.mockResolvedValue([])
    const user = userEvent.setup()
    render(<FacultyShell />)
    await user.click(screen.getByRole('button', { name: 'Show navigation' }))
    await user.click(screen.getByRole('button', { name: 'Students', exact: true }))
    expect(screen.getByRole('button', { name: 'Close navigation' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Record history' }))
    expect(screen.queryByRole('button', { name: 'Close navigation' })).not.toBeInTheDocument()
    expect(window.location.pathname).toBe('/faculty/students/record-history')
  })
  it('opens the implemented tests workflow in the existing shell', async () => {
    const user = userEvent.setup()
    render(<FacultyShell />)
    await user.click(screen.getByRole('button', { name: 'Tests & Assessments' }))
    expect(await screen.findByRole('heading', { name: 'Tests & Examinations' })).toBeInTheDocument()
    expect(screen.queryByText('Coming Soon')).not.toBeInTheDocument()
  })
  it('renders the faculty navigation with verified capabilities and Coming Soon sections', () => {
    render(<FacultyShell />)
    const nav = screen.getByRole('navigation', { name: 'Faculty navigation' })
    expect(nav).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'My Sections' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Students' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Attendance' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Results' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Notices' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Learning Resources' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'AI Assistant' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Profile' })).toBeInTheDocument()
  })

  it('renders an inert Coming Soon placeholder for each section without a backend contract', async () => {
    const user = userEvent.setup()
    render(<FacultyShell />)
    for (const label of ['Notices', 'Learning Resources']) {
      await user.click(screen.getByRole('button', { name: label }))
      expect(screen.getByRole('heading', { name: label, level: 1 })).toBeInTheDocument()
      expect(screen.getByText('Coming Soon')).toBeInTheDocument()
      expect(
        screen.getByText('No information is available for this section yet.'),
      ).toBeInTheDocument()
      // Inert placeholder: no data rows, no actions, no assistant.
      expect(screen.queryByRole('button', { name: /open|save|delete|submit/i })).not.toBeInTheDocument()
      expect(chatShellSpy).not.toHaveBeenCalled()
    }
  })

  it('never performs a request when browsing Coming Soon sections', async () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    const user = userEvent.setup()
    render(<FacultyShell />)
    for (const label of ['Notices', 'Learning Resources']) {
      await user.click(screen.getByRole('button', { name: label }))
    }
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('never renders admin navigation', () => {
    render(<FacultyShell />)
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  })

  it('marks the active navigation item with aria-current', () => {
    render(<FacultyShell />)
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('button', { name: 'AI Assistant' })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('renders the dashboard heading by default', () => {
    render(<FacultyShell />)
    expect(screen.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeInTheDocument()
  })

  it('navigates to the AI Assistant and reuses the existing ChatShell', async () => {
    const user = userEvent.setup()
    render(<FacultyShell />)
    await user.click(screen.getByRole('button', { name: 'AI Assistant' }))
    // The assistant view is the existing ChatShell inside a labelled section
    // (the shell renders no page h1 for the assistant, matching StudentShell).
    expect(screen.getByRole('region', { name: 'AI Assistant' })).toBeInTheDocument()
    expect(chatShellSpy).toHaveBeenCalled()
  })

  it('opens the upload attendance workflow from the faculty sidebar when no assignment exists', async () => {
    facultyAttendanceApi.getFacultyAttendanceAssignments.mockResolvedValue([])
    facultyAttendanceApi.getFacultyAttendanceRoster.mockResolvedValue([])
    const user = userEvent.setup()
    render(<FacultyShell />)

    await user.click(screen.getByRole('button', { name: 'Attendance' }))
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))

    const dialog = await screen.findByRole('dialog', { name: 'Upload Attendance' })
    expect(within(dialog).getByRole('heading', { name: 'No Active Assignments' })).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'View My Sections' })).toBeInTheDocument()
  })

  it('navigates to the profile view', async () => {
    const user = userEvent.setup()
    render(<FacultyShell />)
    await user.click(screen.getByRole('button', { name: 'Profile' }))
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
  })

  it('shows a controlled neutral state when the identity is missing', () => {
    authState.user = null
    render(<FacultyShell />)
    expect(screen.getByRole('heading', { name: 'Faculty workspace unavailable' })).toBeInTheDocument()
  })

  it('offers sign out', async () => {
    const user = userEvent.setup()
    render(<FacultyShell />)
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)
  })
})

/**
 * Phase 6.18 — Staff shell tests.
 *
 * The shell is selected from the server-authoritative /auth/me role; these
 * tests verify the staff navigation, active state, assistant entry
 * (existing ChatShell reuse), approvals entry, and that no admin/student
 * surface is ever rendered for the staff role.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StaffShell from './StaffShell.tsx'
import type { CurrentUser } from '../../types/auth.ts'

const authState = vi.hoisted(() => ({
  status: 'authenticated' as string,
  user: null as CurrentUser | null,
  role: null as string | null,
  accessToken: 'test-token' as string | null,
  error: null as string | null,
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('../auth/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

const chatShellSpy = vi.hoisted(() => vi.fn())
vi.mock('../chat/ChatShell.tsx', () => ({
  default: function ChatShellMock() {
    chatShellSpy('ChatShell rendered')
    return <div>ChatShellMock</div>
  },
}))

vi.mock('../../services/adminApi.ts', () => ({
  AdminApiError: class AdminApiError extends Error {
    readonly status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
  listPendingStudents: vi.fn().mockResolvedValue([]),
  approvePendingStudent: vi.fn(),
  rejectPendingStudent: vi.fn(),
}))

const STAFF_USER: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  email: 'staff@college.edu',
  role: 'staff',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

beforeEach(() => {
  authState.status = 'authenticated'
  authState.user = STAFF_USER
  authState.role = 'staff'
  authState.accessToken = 'test-token'
  authState.error = null
  authState.logout.mockReset()
  chatShellSpy.mockClear()
})

describe('StaffShell', () => {
  it('renders the staff navigation with only verified surfaces', () => {
    render(<StaffShell />)
    const nav = screen.getByRole('navigation', { name: 'Staff navigation' })
    expect(nav).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Student Approvals' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'AI Assistant' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Profile' })).toBeInTheDocument()
  })

  it('never renders admin, student, or faculty navigation', () => {
    render(<StaffShell />)
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Faculty navigation' })).not.toBeInTheDocument()
    // Admin-only management surfaces are absent.
    expect(screen.queryByRole('button', { name: 'Notice Management' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'User Management' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Role Management' })).not.toBeInTheDocument()
  })

  it('marks the active navigation item with aria-current', () => {
    render(<StaffShell />)
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('button', { name: 'AI Assistant' })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('renders the dashboard heading by default', () => {
    render(<StaffShell />)
    expect(screen.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeInTheDocument()
  })

  it('navigates to the AI Assistant and reuses the existing ChatShell', async () => {
    const user = userEvent.setup()
    render(<StaffShell />)
    await user.click(screen.getByRole('button', { name: 'AI Assistant' }))
    // The assistant view is the existing ChatShell inside a labelled section
    // (the shell renders no page h1 for the assistant, matching StudentShell).
    expect(screen.getByRole('region', { name: 'AI Assistant' })).toBeInTheDocument()
    expect(chatShellSpy).toHaveBeenCalled()
  })

  it('navigates to the approvals view', async () => {
    const user = userEvent.setup()
    render(<StaffShell />)
    await user.click(screen.getByRole('button', { name: 'Student Approvals' }))
    expect(screen.getByRole('heading', { name: 'Student Approvals', level: 1 })).toBeInTheDocument()
  })

  it('navigates to the profile view', async () => {
    const user = userEvent.setup()
    render(<StaffShell />)
    await user.click(screen.getByRole('button', { name: 'Profile' }))
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
  })

  it('shows a controlled neutral state when the identity is missing', () => {
    authState.user = null
    render(<StaffShell />)
    expect(screen.getByRole('heading', { name: 'Staff workspace unavailable' })).toBeInTheDocument()
  })

  it('offers sign out', async () => {
    const user = userEvent.setup()
    render(<StaffShell />)
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)
  })
})

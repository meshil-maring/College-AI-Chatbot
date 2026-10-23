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

vi.mock('../auth/session/AuthProvider.tsx', () => ({
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

vi.mock('../../services/admin/adminApi.ts', () => ({
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
  effective_permissions: ['profile.own.read', 'ai.chat', 'students.read', 'students.approve', 'students.reject'],
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

describe('staff account workspace', () => {
  it('starts on the profile with account approvals and chat navigation', () => {
    render(<StaffShell />)
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Profile' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: 'Student Approvals' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Students', exact: true })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Attendance' })).not.toBeInTheDocument()
  })
  it('opens account decisions without academic roster or registration controls', async () => {
    render(<StaffShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Student Approvals' }))
    expect(await screen.findByText('No students are awaiting approval right now.')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Students pages' })).not.toBeInTheDocument()
  })
  it('reuses the assistant and sign-out flow', async () => {
    render(<StaffShell />)
    await userEvent.click(screen.getByRole('button', { name: 'AI Assistant' }))
    expect(chatShellSpy).toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledOnce()
  })
  it('does not render a workspace with no identity', () => {
    authState.user = null
    render(<StaffShell />)
    expect(screen.queryByRole('navigation', { name: 'Staff navigation' })).not.toBeInTheDocument()
  })
})

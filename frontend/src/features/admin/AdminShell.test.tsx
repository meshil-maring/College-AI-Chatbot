import './__tests__/AdminShell.support.tsx'
import { authState } from './__tests__/AdminShell.support.tsx'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import * as adminApi from '../../services/admin/adminApi.ts'
import AdminShell from './AdminShell.tsx'

describe('administrator account workspace', () => {
  it('starts on the account profile without reading retired academic data', () => {
    render(<AdminShell />)
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('Signed in as admin@test.com')).toBeInTheDocument()
    expect(adminApi.getAdminIdentity).not.toHaveBeenCalled()
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    expect(
      within(nav)
        .getAllByRole('button')
        .map((item) => item.textContent),
    ).toEqual([
      'Profile',
      'Academic Setup',
      'Staff & Faculty',
      'Student Approvals',
      'Notices',
      'Documents',
      'FAQs',
      'AI Assistant',
      'Staff Permissions',
    ])
    for (const value of ['u1', 'a1', 'inst-1', 'test-token']) {
      expect(screen.queryByText(value, { exact: true })).not.toBeInTheDocument()
    }
  })
  it('keeps student account approvals available without a roster submenu', async () => {
    render(<AdminShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Student Approvals', exact: true }))
    expect(await screen.findByText('No students are awaiting approval right now.')).toBeInTheDocument()
    expect(adminApi.listPendingStudents).toHaveBeenCalledWith('test-token')
    expect(screen.queryByRole('navigation', { name: 'Students pages' })).not.toBeInTheDocument()
  })
  it('enforces the whole approval permission set in navigation', () => {
    authState.user.effective_permissions = ['profile.own.read', 'students.read', 'students.approve']
    render(<AdminShell />)
    expect(screen.queryByRole('button', { name: 'Student Approvals' })).not.toBeInTheDocument()
  })
  it('reuses chat and the existing sign-out lifecycle', async () => {
    render(<AdminShell />)
    await userEvent.click(screen.getByRole('button', { name: 'AI Assistant' }))
    expect(screen.getByText('AI Assistant chat')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledOnce()
  })
  it('does not mount an administrator workspace for another role', () => {
    authState.role = 'student'
    render(<AdminShell />)
    expect(screen.queryByRole('navigation', { name: 'Admin navigation' })).not.toBeInTheDocument()
  })
})

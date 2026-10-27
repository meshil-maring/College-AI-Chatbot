import './__tests__/AdminShell.support.tsx'
import { authState } from './__tests__/AdminShell.support.tsx'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import * as adminApi from '../../services/admin/adminApi.ts'
import * as academicApi from '../../services/admin/academics.ts'
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
  it('opens the redesigned overview and its expanded academic navigation', async () => {
    render(<AdminShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Academic Setup', exact: true }))
    expect(screen.getByRole('heading', { name: 'Academic Setup', level: 1 })).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(9)
    const nav = screen.getByRole('navigation', { name: 'Academic Setup navigation' })
    await userEvent.click(within(nav).getByRole('button', { name: 'Academic Terms', exact: true }))
    expect(screen.getByRole('heading', { name: 'Academic Terms', level: 1 })).toBeInTheDocument()
    expect(screen.getByText(/when teaching takes place, not program progression/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Student Approvals', exact: true })).toBeInTheDocument()
  })
  it('supports desktop navigation collapse and search from the academic header', async () => {
    render(<AdminShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Academic Setup', exact: true }))
    const toggle = screen.getByRole('button', { name: 'Toggle navigation' })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await userEvent.click(toggle)
    const search = screen.getByRole('searchbox', { name: 'Search academic setup' })
    await userEvent.type(search, 'curricula')
    const results = screen.getByRole('region', { name: 'Academic management areas' })
    expect(within(results).getByRole('heading', { name: 'Curriculum Versions' })).toBeInTheDocument()
    expect(within(results).getByRole('heading', { name: 'Curriculum Subjects' })).toBeInTheDocument()
  })
  it('shows the design overview for an admin with the nonacademic grants in the reported sidebar', async () => {
    authState.user.effective_permissions = [
      'profile.own.read',
      'users.read',
      'students.read',
      'students.approve',
      'students.reject',
      'notices.read',
      'documents.read',
      'ai.knowledge.read',
      'ai.chat',
      'permissions.read',
    ]
    render(<AdminShell />)
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    await userEvent.click(within(nav).getByRole('button', { name: 'Academic Setup', exact: true }))
    expect(screen.getByRole('heading', { name: 'Academic Setup', level: 1 })).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(9)
    expect(screen.getByRole('status')).toHaveTextContent('Design preview')
    expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeDisabled()
    expect(academicApi.getAcademicSetup).not.toHaveBeenCalled()
    expect(academicApi.createAcademicRecord).not.toHaveBeenCalled()
  })
})

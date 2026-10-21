import './__tests__/AdminShell.support.tsx'
import { authState } from './__tests__/AdminShell.support.tsx'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import * as adminApi from '../../services/admin/adminApi.ts'
import { buildDashboardSummary } from '../../test/adminDashboardFixtures.ts'
import type { AcademicCatalogue } from '../../types/academicSetup.ts'
import AdminShell from './AdminShell.tsx'
describe('AdminShell', () => {
  it('renders the admin panel with the canonical identity from auth state', () => {
    render(<AdminShell />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByText('Signed in as admin@test.com')).toBeInTheDocument()
  })

  it('never probes GET /admin/me for role detection', () => {
    render(<AdminShell />)
    expect(adminApi.getAdminIdentity).not.toHaveBeenCalled()
  })

  it('renders the fail-closed admin navigation with real capabilities', () => {
    render(<AdminShell />)
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    expect(nav).toBeInTheDocument()
    for (const label of [
      'Dashboard',
      'Students',
      'Attendance',
      'Results',
      'Test Results',
      'Notices',
      'Documents',
      'FAQs',
      'AI Assistant',
      'Profile',
      'Staff Permissions',
      'Faculty Assignments',
    ]) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  it('renders no admin navigation for non-admin roles (fail closed)', () => {
    authState.role = 'student'
    render(<AdminShell />)
    expect(screen.queryByRole('navigation', { name: 'Admin navigation' })).not.toBeInTheDocument()
  })

  it('marks the active view with aria-current', () => {
    render(<AdminShell />)
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
  })

  it('switches to the profile view showing only safe identity fields', async () => {
    const user = userEvent.setup()
    render(<AdminShell />)
    await user.click(screen.getByRole('button', { name: 'Profile' }))
    await waitFor(() => {
      expect(screen.getByText('Administrator identity')).toBeInTheDocument()
    })
    expect(within(screen.getByRole('main')).getByText('admin@test.com')).toBeInTheDocument()
    // Security: no token material or internal identifiers in the DOM.
    expect(screen.queryByText('test-token')).not.toBeInTheDocument()
    expect(screen.queryByText('u1')).not.toBeInTheDocument()
    expect(screen.queryByText('a1')).not.toBeInTheDocument()
    expect(screen.queryByText('inst-1')).not.toBeInTheDocument()
  })

  it('lands on the Dashboard by default and routes quick actions to real views', async () => {
    // Phase 7.21: Dashboard is the default landing view, and a quick action
    // switches the shell to the EXISTING screen it names — no second dashboard.
    vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(buildDashboardSummary())
    vi.mocked(adminApi.listPendingStudents).mockReset()
    vi.mocked(adminApi.listPendingStudents).mockResolvedValue([])
    const user = userEvent.setup()
    render(<AdminShell />)
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Key metrics' })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    await user.click(screen.getByRole('button', { name: /Approve Student/ }))
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Waiting approval' })).toHaveAttribute('aria-current', 'page')
    })
    // Exactly one Dashboard navigation entry still exists.
    expect(screen.getAllByRole('button', { name: 'Dashboard' })).toHaveLength(1)
  })

  it('signs out via the shared logout', async () => {
    const user = userEvent.setup()
    render(<AdminShell />)
    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)
  })

  it('uses the faculty submenu, keeps both methods in Register, and supports Back, Forward and reload', async () => {
    vi.mocked(adminApi.listStudents).mockResolvedValue([])
    const user = userEvent.setup()
    const first = render(<AdminShell />)
    await user.click(screen.getByRole('button', { name: 'Students', exact: true }))
    const pages = screen.getByRole('navigation', { name: 'Students pages' })
    expect(
      within(pages)
        .getAllByRole('link')
        .map((link) => link.textContent),
    ).toEqual(['Roster', 'Record history', 'Waiting approval', 'Register'])
    expect(screen.queryByRole('button', { name: 'Student Approvals' })).not.toBeInTheDocument()
    await user.click(within(pages).getByRole('link', { name: 'Register', exact: true }))
    await user.click(screen.getByRole('tab', { name: 'Bulk Registration' }))
    expect(window.location.hash).toBe('#admin/students/register?method=bulk')
    expect(screen.getByRole('link', { name: 'Register', exact: true })).toHaveAttribute('aria-current', 'page')
    expect(within(pages).queryByRole('link', { name: 'Bulk Import' })).not.toBeInTheDocument()
    act(() => window.history.back())
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Individual Registration' })).toHaveAttribute('aria-selected', 'true'),
    )
    act(() => window.history.forward())
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Bulk Registration' })).toHaveAttribute('aria-selected', 'true'),
    )
    first.unmount()
    render(<AdminShell />)
    expect(await screen.findByRole('tab', { name: 'Bulk Registration' })).toHaveAttribute('aria-selected', 'true')
  })

  it('marks restricted submenu pages unavailable without granting access', async () => {
    authState.user.effective_permissions = ['students.read', 'profile.own.read']
    vi.mocked(adminApi.listStudents).mockResolvedValue([])
    render(<AdminShell />)
    await userEvent.click(screen.getByRole('button', { name: 'Students', exact: true }))
    const pages = screen.getByRole('navigation', { name: 'Students pages' })
    expect(within(pages).getByText('Record history')).toHaveAttribute('aria-disabled', 'true')
    expect(within(pages).getByText('Waiting approval')).toHaveAttribute('aria-disabled', 'true')
  })

  function mockAcademicNavigation() {
    const catalogue: AcademicCatalogue = {
      institution_id: 'inst-1',
      manageable: ['departments'],
      records: { departments: [{ department_id: 'department-1', name: 'Science', code: 'SCI', is_active: true }] },
    }
    vi.mocked(adminApi.getAcademicCatalogue).mockReset().mockResolvedValue(catalogue)
    vi.mocked(adminApi.getFacultyAssignments)
      .mockReset()
      .mockResolvedValue({ faculty: [], sections: [], assignments: [] })
    vi.mocked(adminApi.getFacultyResponsibilityManagement)
      .mockReset()
      .mockResolvedValue({ faculty: [], definitions: [], departments: [], sections: [], responsibilities: [] })
    return catalogue
  }

  function navigate(label: string) {
    fireEvent.click(
      within(screen.getByRole('navigation', { name: 'Admin navigation' })).getByRole('button', { name: label }),
    )
  }

  it('reuses academic and faculty data when navigating between their screens', async () => {
    mockAcademicNavigation()
    render(<AdminShell />)
    navigate('Academic Setup')
    await screen.findByText('SCI · Science')
    navigate('Faculty Assignments')
    await screen.findByText('No active Faculty assignments.')
    await screen.findByText('Select a faculty member to view their responsibilities.')
    expect(screen.getAllByRole('heading', { name: 'Faculty Assignments', level: 1 })).toHaveLength(1)
    navigate('Academic Setup')
    expect(screen.getByText('SCI · Science')).toBeInTheDocument()
    expect(screen.queryByText('Loading academic setup…')).not.toBeInTheDocument()
    navigate('Faculty Assignments')
    expect(screen.getByText('No active Faculty assignments.')).toBeInTheDocument()
    expect(screen.queryByText('Loading Faculty assignments…')).not.toBeInTheDocument()
    expect(adminApi.getAcademicCatalogue).toHaveBeenCalledTimes(1)
    expect(adminApi.getFacultyAssignments).toHaveBeenCalledTimes(1)
    expect(adminApi.getFacultyResponsibilityManagement).toHaveBeenCalledTimes(1)
  })

  it('refreshes cached faculty options after academic changes and reuses the saved catalogue', async () => {
    mockAcademicNavigation()
    vi.mocked(adminApi.saveAcademicRecord).mockReset().mockResolvedValue({ saved: true })
    render(<AdminShell />)
    navigate('Faculty Assignments')
    await screen.findByText('No active Faculty assignments.')
    await screen.findByText('Select a faculty member to view their responsibilities.')
    navigate('Academic Setup')
    fireEvent.click(await screen.findByRole('button', { name: 'Edit SCI' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Updated Science' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save record' }))
    await waitFor(() => expect(adminApi.getAcademicCatalogue).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Edit SCI' })).toBeEnabled())
    expect(adminApi.getFacultyAssignments).toHaveBeenCalledTimes(1)
    navigate('Faculty Assignments')
    await waitFor(() => expect(adminApi.getFacultyAssignments).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(adminApi.getFacultyResponsibilityManagement).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByText('Updating Faculty assignments…')).not.toBeInTheDocument())
    navigate('Academic Setup')
    expect(screen.getByText('SCI · Science')).toBeInTheDocument()
    expect(adminApi.getAcademicCatalogue).toHaveBeenCalledTimes(2)
  })

  it('allows manually refreshing academic records within the freshness window', async () => {
    const catalogue = mockAcademicNavigation()
    render(<AdminShell />)
    navigate('Academic Setup')
    await screen.findByText('SCI · Science')
    vi.mocked(adminApi.getAcademicCatalogue).mockResolvedValue({
      ...catalogue,
      records: { departments: [{ department_id: 'department-1', name: 'New Science', code: 'SCI', is_active: true }] },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Refresh academic setup' }))
    expect(await screen.findByText('SCI · New Science')).toBeInTheDocument()
    expect(adminApi.getAcademicCatalogue).toHaveBeenCalledTimes(2)
  })
})

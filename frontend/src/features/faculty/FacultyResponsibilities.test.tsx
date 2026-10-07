import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyShell from './FacultyShell.tsx'
import FacultyProfile from './FacultyProfile.tsx'
import FacultyResponsibilityWorkspace from './FacultyResponsibilityWorkspace.tsx'
import { buildFacultyNavigation } from './facultyNavigation.ts'
import { responsibilityPermissions, visibleResponsibilities } from './responsibilities.ts'
import { classResponsibility, facultyContextFixture, hodResponsibility, responsibilityReportFixture } from '../../test/facultyResponsibilitiesFixtures.ts'
import type { CurrentUser } from '../../types/auth.ts'
import * as api from '../../services/adminApi.ts'

const state = vi.hoisted(() => ({ user: null as CurrentUser | null, accessToken: 'jwt', role: 'faculty', logout: vi.fn() }))
vi.mock('../auth/AuthProvider.tsx', () => ({ useAuth: () => state }))
vi.mock('../chat/ChatShell.tsx', () => ({ default: () => <div>Assistant</div> }))
vi.mock('../../services/adminApi.ts')

const user: CurrentUser = { authenticated: true, user_id: 'faculty-1', auth_user_id: 'auth-1', role: 'faculty', institution_id: 'institution-1', email: 'ada@example.test', effective_permissions: ['profile.own.read', 'faculty.assignments.read', 'attendance.read'], faculty_context: facultyContextFixture }
beforeEach(() => {
  vi.clearAllMocks(); state.user = user
  vi.mocked(api.getFacultyContext).mockResolvedValue(facultyContextFixture)
  vi.mocked(api.getFacultyResponsibilityReport).mockResolvedValue(responsibilityReportFixture)
})
afterEach(() => vi.useRealTimers())

describe('Faculty responsibilities', () => {
  it.each([
    [[], []], [[hodResponsibility], ['Department']], [[classResponsibility], ['Class Management']],
    [[hodResponsibility, classResponsibility], ['Class Management', 'Department']],
  ])('adds navigation from scoped capabilities %j', (responsibilities, labels) => {
    const context = { ...facultyContextFixture, responsibilities }
    const navigation = buildFacultyNavigation('faculty', [], responsibilityPermissions(context))
    expect(navigation.filter((item) => ['class-management', 'department'].includes(item.key)).map((item) => item.label)).toEqual(labels)
    expect(buildFacultyNavigation('student', [], responsibilityPermissions(context))).toEqual([])
  })

  it('filters expired, future, inactive, and revoked responsibilities', () => {
    const now = Date.now()
    for (const changes of [{ end_at: new Date(now).toISOString() }, { start_at: new Date(now + 1).toISOString() }, { is_active: false }, { revoked_at: new Date(now).toISOString() }]) {
      expect(visibleResponsibilities({ ...facultyContextFixture, responsibilities: [{ ...hodResponsibility, ...changes }] }, now)).toEqual([])
    }
  })

  it('shows combined responsibilities and separate teaching assignments in the profile', () => {
    render(<FacultyProfile user={user} />)
    expect(screen.getByText('HOD — CSE Department')).toBeInTheDocument()
    expect(screen.getByText('Class In-Charge — B.Tech CSE · Semester 5 · Section A')).toBeInTheDocument()
    expect(screen.getByText(/Data Mining — B.Tech CSE/)).toBeInTheDocument()
  })

  it('uses the same Faculty shell for both positions and removes revoked links after refresh', async () => {
    render(<FacultyShell />)
    await waitFor(() => expect(api.getFacultyContext).toHaveBeenCalled())
    expect(screen.getByRole('button', { name: 'Department' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Class Management' })).toBeInTheDocument()
    vi.mocked(api.getFacultyContext).mockResolvedValue({ responsibilities: [], teaching_assignments: [], responsibility_permissions: [] })
    fireEvent.focus(window)
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Department' })).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Class Management' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Attendance' })).toBeInTheDocument()
  })

  it('removes expired navigation at the validity boundary', async () => {
    vi.useFakeTimers()
    const expiring = { ...facultyContextFixture, responsibilities: [{ ...hodResponsibility, end_at: new Date(Date.now() + 1000).toISOString() }] }
    state.user = { ...user, faculty_context: expiring }
    vi.mocked(api.getFacultyContext).mockResolvedValue(expiring)
    render(<FacultyShell />)
    expect(screen.getByRole('button', { name: 'Department' })).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1100) })
    expect(screen.queryByRole('button', { name: 'Department' })).not.toBeInTheDocument()
  })

  it('clears scoped views on a failed authorization refresh and keeps stale profile data hidden', async () => {
    render(<FacultyShell />)
    await waitFor(() => expect(api.getFacultyContext).toHaveBeenCalled())
    vi.mocked(api.getFacultyContext).mockRejectedValue(new Error('Forbidden'))
    fireEvent.focus(window)
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be refreshed')
    expect(screen.queryByRole('button', { name: 'Department' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Profile' }))
    expect(screen.queryByText('HOD — CSE Department')).not.toBeInTheDocument()
  })

  it('shows section reports and low attendance without edit controls', async () => {
    render(<FacultyResponsibilityWorkspace accessToken="jwt" context={facultyContextFixture} permission="academic.department.read" />)
    await screen.findByRole('button', { name: 'Low Attendance' })
    fireEvent.click(screen.getByRole('button', { name: 'Low Attendance' }))
    expect(screen.getByText('Student One')).toBeInTheDocument()
    expect(screen.getByText('70% (7/10)')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /mark|save|edit/i })).not.toBeInTheDocument()
  })

  it('handles report 403 without displaying cached data or claiming access', async () => {
    vi.mocked(api.getFacultyResponsibilityReport).mockRejectedValue(new Error('Active responsibility not found'))
    render(<FacultyResponsibilityWorkspace accessToken="jwt" context={facultyContextFixture} permission="academic.class.read" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Active responsibility not found')
    expect(screen.queryByText('Student One')).not.toBeInTheDocument()
  })
})

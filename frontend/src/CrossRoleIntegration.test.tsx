import './__tests__/CrossRoleIntegration.support.tsx'
import {
  ADMIN_B,
  authState,
  FACULTY_A,
  FORBIDDEN_LABELS,
  NAV_LANDMARKS,
  navigationLabels,
  ROLES,
  setIdentity,
  STAFF_A,
  STUDENT_B,
} from './__tests__/CrossRoleIntegration.support.tsx'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import Application from './App.tsx'
import { QueryProvider } from './providers/QueryProvider.tsx'
import { ADMIN_NAV_ITEMS } from './features/admin/adminNavigation.ts'
import { FACULTY_NAV_ITEMS } from './features/faculty/workspace/facultyNavigation.ts'
import { STAFF_NAV_ITEMS } from './features/staff/staffNavigation.ts'
import { STUDENT_NAV_ITEMS } from './features/student/workspace/studentNavigation.ts'
function App() {
  return (
    <QueryProvider>
      <Application />
    </QueryProvider>
  )
}
describe('role -> shell matrix', () => {
  it('renders AdminShell for the admin role only', () => {
    render(<App />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Admin navigation' })).toBeInTheDocument()
    for (const other of ['staff', 'faculty', 'student']) {
      expect(screen.queryByRole('navigation', { name: NAV_LANDMARKS[other] })).not.toBeInTheDocument()
    }
  })

  it('renders StaffShell for the staff role only', () => {
    setIdentity(STAFF_A, 'staff')
    render(<App />)
    expect(screen.getByRole('navigation', { name: 'Staff navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Faculty navigation' })).not.toBeInTheDocument()
  })

  it('renders FacultyShell for the faculty role only', () => {
    setIdentity(FACULTY_A, 'faculty')
    render(<App />)
    expect(screen.getByRole('navigation', { name: 'Faculty navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  })

  it('renders StudentShell for the student role only', async () => {
    setIdentity(STUDENT_B, 'student')
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Staff navigation' })).not.toBeInTheDocument()
  })

  it('fails safe for a null and an unknown role: no shell, no navigation, sign-out only', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<App />)

    // An AUTHENTICATED account whose /auth/me role resolves to null (no
    // supported role) and an unknown role value both fail closed.
    for (const role of [null, 'unknown-role'] as const) {
      setIdentity(null, role)
      rerender(<App />)
      expect(screen.getByText('Access restricted')).toBeInTheDocument()
      for (const landmark of Object.values(NAV_LANDMARKS)) {
        expect(screen.queryByRole('navigation', { name: landmark })).not.toBeInTheDocument()
      }
      expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    }

    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)
  })
})

describe('role -> navigation isolation', () => {
  it('renders exactly its own navigation model for each role', async () => {
    const { rerender } = render(<App />)

    expect(await navigationLabels('admin')).toEqual(ADMIN_NAV_ITEMS.map((item) => item.label))

    setIdentity(STAFF_A, 'staff')
    rerender(<App />)
    expect(await navigationLabels('staff')).toEqual(STAFF_NAV_ITEMS.map((item) => item.label))

    setIdentity(FACULTY_A, 'faculty')
    rerender(<App />)
    expect(await navigationLabels('faculty')).toEqual(FACULTY_NAV_ITEMS.map((item) => item.label))

    setIdentity(STUDENT_B, 'student')
    rerender(<App />)
    expect(await navigationLabels('student')).toEqual(STUDENT_NAV_ITEMS.map((item) => item.label))
  })

  it("never exposes another role's navigation entries", async () => {
    const { rerender } = render(<App />)

    for (const [role, user] of ROLES) {
      setIdentity(user, role)
      rerender(<App />)
      const labels = await navigationLabels(role)
      for (const forbidden of FORBIDDEN_LABELS[role]) {
        expect(labels, `${role} navigation must not expose "${forbidden}"`).not.toContain(forbidden)
      }
    }
  })

  it('keeps staff approvals without administrator-only management views', async () => {
    setIdentity(STAFF_A, 'staff')
    render(<App />)
    const labels = await navigationLabels('staff')
    expect(labels).toContain('Student Approvals')
    for (const adminOnly of ['Academic Setup', 'Staff Permissions', 'FAQs']) {
      expect(labels).not.toContain(adminOnly)
    }
  })
})

describe('role transition safety', () => {
  it('admin -> student leaves no admin shell, navigation, or dashboard state', async () => {
    const { rerender } = render(<App />)
    // Phase 7.21: the admin dashboard is identified by its labelled overview
    // region rather than the removed flat "Overview" heading.
    expect(screen.getByRole('heading', { name: 'Profile', level: 1 })).toBeInTheDocument()

    setIdentity(STUDENT_B, 'student')
    rerender(<App />)

    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Admin navigation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Institution overview' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Key metrics' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Quick actions' })).not.toBeInTheDocument()
    expect(screen.queryByText('Signed in as admin.a@college.edu')).not.toBeInTheDocument()
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
  })

  it('walks every transition without inheriting the previous role', async () => {
    const { rerender } = render(<App />)

    for (const [role, user] of ROLES) {
      setIdentity(user, role)
      rerender(<App />)
      expect(await screen.findByRole('navigation', { name: NAV_LANDMARKS[role] })).toBeInTheDocument()
      for (const other of Object.keys(NAV_LANDMARKS)) {
        if (other === role) continue
        expect(screen.queryByRole('navigation', { name: NAV_LANDMARKS[other] })).not.toBeInTheDocument()
      }
      // Only the current identity is rendered.
      expect(screen.getByText(`Signed in as ${user.email}`)).toBeInTheDocument()
      for (const forbidden of FORBIDDEN_LABELS[role]) {
        expect(await navigationLabels(role)).not.toContain(forbidden)
      }
    }
  })

  it('logout then login as another role never resurrects the previous shell', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<App />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)

    // The (real) AuthProvider clears the session on logout: status becomes
    // unauthenticated, so the public gateway is rendered.
    setIdentity(null, null, 'unauthenticated')
    rerender(<App />)
    expect(screen.getByRole('heading', { name: 'College AI Platform' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()

    // A different account signs in: the student shell, with no admin residue.
    setIdentity(STUDENT_B, 'student')
    rerender(<App />)
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })
})

describe('stale view-state protection', () => {
  it('resets an admin view when the SAME role is replaced by another account', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<App />)

    await user.click(screen.getByRole('button', { name: 'Learning Resources' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Learning Resources' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Learning Resources' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('Signed in as admin.a@college.edu')).toBeInTheDocument()

    // Same role, DIFFERENT account/tenant — the status never leaves
    // 'authenticated', so only the identity-scoped shell key can discard
    // tenant A's view state and already-fetched admin data.
    setIdentity(ADMIN_B, 'admin')
    rerender(<App />)

    expect(screen.getByRole('button', { name: 'Profile' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('heading', { level: 1, name: 'Learning Resources' })).not.toBeInTheDocument()
    expect(screen.queryByText('Signed in as admin.a@college.edu')).not.toBeInTheDocument()
    expect(screen.getByText('Signed in as admin.b@college.edu')).toBeInTheDocument()
  })

  it('resets a staff approval view before a student session mounts', async () => {
    const user = userEvent.setup()
    setIdentity(STAFF_A, 'staff')
    const { rerender } = render(<App />)

    await user.click(screen.getByRole('button', { name: 'Student Approvals', exact: true }))
    expect(await screen.findByText('No students are awaiting approval right now.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'All Student' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Register', exact: true })).not.toBeInTheDocument()

    setIdentity(STUDENT_B, 'student')
    rerender(<App />)

    expect(screen.queryByRole('link', { name: 'Waiting approval' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Student Approvals', exact: true })).not.toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Profile' })).toHaveAttribute('aria-current', 'page')
  })
})

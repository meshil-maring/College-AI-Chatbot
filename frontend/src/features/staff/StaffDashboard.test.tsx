/**
 * Phase 6.18 — Staff identity, profile, and dashboard tests.
 *
 * Covers: safe identity rendering, verified workspace surfaces, entry
 * points, and the security assertions (no internal IDs / tokens rendered;
 * no fabricated operational data).
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StaffDashboard from './StaffDashboard.tsx'
import StaffProfile from './StaffProfile.tsx'
import StaffIdentityCard from './StaffIdentityCard.tsx'
import type { CurrentUser } from '../../types/auth.ts'

const STAFF_USER: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  email: 'staff@college.edu',
  role: 'staff',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

describe('StaffIdentityCard', () => {
  it('renders the staff identity with safe fields only', () => {
    render(<StaffIdentityCard user={STAFF_USER} />)
    expect(screen.getByRole('heading', { name: 'Staff identity' })).toBeInTheDocument()
    expect(screen.getByText('staff@college.edu')).toBeInTheDocument()
    expect(screen.getByText('Staff')).toBeInTheDocument()
    expect(screen.getByText('Linked to your institution')).toBeInTheDocument()
  })

  it('never renders internal identifiers or token material', () => {
    const { container } = render(<StaffIdentityCard user={STAFF_USER} />)
    const text = container.textContent ?? ''
    expect(text).not.toContain(STAFF_USER.user_id)
    expect(text).not.toContain(STAFF_USER.auth_user_id)
    expect(text).not.toContain(STAFF_USER.institution_id)
    expect(text.toLowerCase()).not.toContain('bearer')
    expect(text.toLowerCase()).not.toContain('token')
  })

  it('shows a neutral institution state when no tenant is linked', () => {
    render(<StaffIdentityCard user={{ ...STAFF_USER, institution_id: null }} />)
    expect(screen.getByText('No institution linked')).toBeInTheDocument()
  })
})

describe('StaffDashboard', () => {
  it('renders the verified workspace surfaces', () => {
    render(<StaffDashboard user={STAFF_USER} onNavigate={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Operational workspace' })).toBeInTheDocument()
    expect(screen.getByText('Student Approvals')).toBeInTheDocument()
    expect(screen.getByText('AI Assistant')).toBeInTheDocument()
    expect(screen.getByText('Attendance')).toBeInTheDocument()
    expect(screen.getByText('Notices')).toBeInTheDocument()
    expect(screen.getAllByText('Not available yet').length).toBeGreaterThan(0)
  })

  it('never fabricates operational counts or statistics', () => {
    const { container } = render(<StaffDashboard user={STAFF_USER} onNavigate={vi.fn()} />)
    const text = container.textContent ?? ''
    expect(text).not.toContain('attendance percentage')
    expect(text).not.toMatch(/pending approvals:\s*\d/i)
    expect(text).not.toContain(STAFF_USER.institution_id)
    expect(text).not.toContain(STAFF_USER.user_id)
    expect(text).not.toContain(STAFF_USER.auth_user_id)
    expect(text.toLowerCase()).not.toContain('token')
  })

  it('navigates to the approvals view from the entry point', async () => {
    const onNavigate = vi.fn()
    const user = userEvent.setup()
    render(<StaffDashboard user={STAFF_USER} onNavigate={onNavigate} />)
    await user.click(screen.getByRole('button', { name: 'Open Student Approvals' }))
    expect(onNavigate).toHaveBeenCalledWith('approvals')
  })

  it('navigates to the assistant view from the entry point', async () => {
    const onNavigate = vi.fn()
    const user = userEvent.setup()
    render(<StaffDashboard user={STAFF_USER} onNavigate={onNavigate} />)
    await user.click(screen.getByRole('button', { name: 'Open AI Assistant' }))
    expect(onNavigate).toHaveBeenCalledWith('assistant')
  })
})

describe('StaffProfile', () => {
  it('renders the identity and the honest no-context statement', () => {
    render(<StaffProfile user={STAFF_USER} />)
    expect(screen.getByRole('heading', { name: 'Staff identity' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Profile details' }),
    ).toBeInTheDocument()
  })

  it('never invents staff profile fields', () => {
    const { container } = render(<StaffProfile user={STAFF_USER} />)
    const text = container.textContent ?? ''
    // No fabricated field VALUES: an employee ID or designation datum would
    // only exist if a backend contract provided one (none does).
    expect(text).not.toMatch(/EMP-\d+/)
    expect(text).not.toMatch(/Designation:\s*\S/)
    expect(text).not.toMatch(/Department:\s*\S/)
    expect(text).not.toContain(STAFF_USER.user_id)
  })
})

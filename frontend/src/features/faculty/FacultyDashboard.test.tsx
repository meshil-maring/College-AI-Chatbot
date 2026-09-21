/**
 * Phase 6.17 — Faculty dashboard tests.
 *
 * Covers: identity rendering, verified workspace surfaces, AI assistant
 * entry point, and the security assertions (no internal IDs / tokens /
 * student secrets rendered).
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FacultyDashboard from './FacultyDashboard.tsx'
import type { CurrentUser } from '../../types/auth.ts'

const FACULTY_USER: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  email: 'faculty@college.edu',
  role: 'faculty',
  institution_id: '30000000-0000-0000-0000-000000000001',
}

function renderDashboard() {
  const onNavigate = vi.fn()
  render(<FacultyDashboard user={FACULTY_USER} onNavigate={onNavigate} />)
  return onNavigate
}

describe('FacultyDashboard identity', () => {
  it('renders the faculty identity with safe fields only', () => {
    renderDashboard()
    expect(screen.getByRole('heading', { name: 'Faculty identity' })).toBeInTheDocument()
    expect(screen.getByText('faculty@college.edu')).toBeInTheDocument()
    expect(screen.getByText('Faculty')).toBeInTheDocument()
  })

  it('never renders internal identifiers or token material', () => {
    const { container } = render(<FacultyDashboard user={FACULTY_USER} onNavigate={vi.fn()} />)
    const text = container.textContent ?? ''
    expect(text).not.toContain(FACULTY_USER.user_id)
    expect(text).not.toContain(FACULTY_USER.auth_user_id)
    expect(text).not.toContain(FACULTY_USER.institution_id)
    expect(text.toLowerCase()).not.toContain('bearer')
    expect(text.toLowerCase()).not.toContain('token')
  })

  it('renders the institution status without the tenant UUID', () => {
    renderDashboard()
    expect(screen.getByText('Linked to your institution')).toBeInTheDocument()
  })
})

describe('FacultyDashboard workspace', () => {
  it('renders the verified workspace surfaces', () => {
    renderDashboard()
    expect(screen.getByRole('heading', { name: 'Academic workspace' })).toBeInTheDocument()
    expect(screen.getByText('AI Assistant')).toBeInTheDocument()
    expect(screen.getByText('Students')).toBeInTheDocument()
    expect(screen.getByText('Attendance')).toBeInTheDocument()
    expect(screen.getByText('Results')).toBeInTheDocument()
    expect(screen.getAllByText('Not available yet').length).toBeGreaterThan(0)
  })

  it('renders the AI assistant entry point that navigates to the assistant', async () => {
    const onNavigate = renderDashboard()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Open AI Assistant' }))
    expect(onNavigate).toHaveBeenCalledWith('assistant')
  })
})

/// <reference types="vitest/globals" />
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import InstitutionManagement from './InstitutionManagement.tsx'
import type { InstitutionDetail, InstitutionSummary } from '../../types/platform.ts'
import type { ReactNode } from 'react'

const listSpy = vi.hoisted(() => vi.fn())
const getSpy = vi.hoisted(() => vi.fn())
const createSpy = vi.hoisted(() => vi.fn())
const suspendSpy = vi.hoisted(() => vi.fn())
const activateSpy = vi.hoisted(() => vi.fn())
const assignSpy = vi.hoisted(() => vi.fn())
const updateSpy = vi.hoisted(() => vi.fn())
const rosterSpy = vi.hoisted(() => vi.fn())
const createInvitationSpy = vi.hoisted(() => vi.fn())
const cancelInvitationSpy = vi.hoisted(() => vi.fn())
const revokeAdminSpy = vi.hoisted(() => vi.fn())

vi.mock('../../services/platformInstitutionsApi.ts', () => ({
  PlatformInstitutionError: class extends Error {},
  listInstitutions: listSpy,
  getInstitution: getSpy,
  createInstitution: createSpy,
  updateInstitution: updateSpy,
  suspendInstitution: suspendSpy,
  activateInstitution: activateSpy,
  assignInstitutionAdmin: assignSpy,
  // Phase 7.14 University Admin lifecycle.
  getAdminRoster: rosterSpy,
  createInvitation: createInvitationSpy,
  cancelInvitation: cancelInvitationSpy,
  revokeInstitutionAdmin: revokeAdminSpy,
}))

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'session-token' }),
}))

const SUMMARY: InstitutionSummary = {
  id: 'inst-1', code: 'UNICO', name: 'Unico University', status: 'active', is_active: true, admin_count: 2,
}
const DETAIL: InstitutionDetail = {
  id: 'inst-1', code: 'UNICO', name: 'Unico University', display_name: null,
  status: 'active', is_active: true, logo_url: null, primary_color: null,
  secondary_color: null, welcome_message: null, created_at: null, updated_at: null, admin_count: 2,
}

function Wrapper({ children }: { children: ReactNode }) {
  return <>{children}</>
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

/**
 * Default empty roster so every Phase 7.13 test renders the detail panel without
 * a pending fetch. Phase 7.14 tests override this per case.
 */
function emptyRoster() {
  return {
    institution_id: 'inst-1',
    admins: [],
    pending_invitations: [],
    admin_count: 0,
  }
}

describe('Super Admin institution management', () => {
  beforeEach(() => {
    // Every test that opens the detail panel needs a roster; the default is empty.
    rosterSpy.mockResolvedValue(emptyRoster())
  })

  it('lists institutions with safe platform metadata only', async () => {
    listSpy.mockResolvedValue([SUMMARY])
    render(<InstitutionManagement />, { wrapper: Wrapper })

    expect(await screen.findByText('Unico University')).toBeDefined()
    expect(screen.getByText('UNICO')).toBeDefined()
    expect(screen.getByText('Active')).toBeDefined()
    // Admin count is shown; no student or credential data is rendered.
    expect(screen.getByText('2')).toBeDefined()
    expect(document.body.textContent).not.toMatch(/password|student record/i)
  })

  it('never exposes the session token in rendered output', async () => {
    listSpy.mockResolvedValue([SUMMARY])
    const { container } = render(<InstitutionManagement />, { wrapper: Wrapper })
    await screen.findByText('Unico University')
    expect(container.textContent).not.toContain('session-token')
  })

  it('creates an institution from name and code alone', async () => {
    listSpy.mockResolvedValue([])
    createSpy.mockResolvedValue(DETAIL)
    getSpy.mockResolvedValue(DETAIL)
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /create institution/i }))
    await userEvent.type(screen.getByLabelText(/institution name/i), 'Demo College')
    await userEvent.type(screen.getByLabelText(/institution code/i), 'DEMO')
    await userEvent.click(screen.getByRole('button', { name: /^create institution$/i }))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith('session-token', { name: 'Demo College', code: 'DEMO' })
    })
  })

  it('requires confirmation before suspending and states data is retained', async () => {
    listSpy.mockResolvedValue([SUMMARY])
    getSpy.mockResolvedValue(DETAIL)
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /manage/i }))
    await userEvent.click(await screen.findByRole('button', { name: /suspend institution/i }))

    const dialog = await screen.findByRole('alertdialog')
    expect(dialog.textContent).toMatch(/data will be retained/i)
    expect(dialog.textContent).toMatch(/no accounts are revoked/i)

    // Cancelling must not call the API.
    await userEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(suspendSpy).not.toHaveBeenCalled()
  })

  it('suspends only after explicit confirmation', async () => {
    listSpy.mockResolvedValue([SUMMARY])
    getSpy.mockResolvedValue(DETAIL)
    suspendSpy.mockResolvedValue({
      id: 'inst-1', code: 'UNICO', name: 'Unico University', status: 'suspended',
      is_active: false, already_applied: false, message: 'Institution suspended.',
    })
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /manage/i }))
    await userEvent.click(await screen.findByRole('button', { name: /suspend institution/i }))
    const dialog = await screen.findByRole('alertdialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /suspend institution/i }))

    await waitFor(() => expect(suspendSpy).toHaveBeenCalledWith('session-token', 'inst-1'))
  })

  it('shows activate instead of suspend for a suspended institution', async () => {
    listSpy.mockResolvedValue([{ ...SUMMARY, status: 'suspended', is_active: false }])
    getSpy.mockResolvedValue({ ...DETAIL, status: 'suspended', is_active: false })
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /manage/i }))
    expect(await screen.findByRole('button', { name: /activate institution/i })).toBeDefined()
    expect(screen.queryByRole('button', { name: /^suspend institution$/i })).toBeNull()
  })

  it('shows an explicit approval action for a pending self-registration', async () => {
    listSpy.mockResolvedValue([{ ...SUMMARY, status: 'pending', is_active: false }])
    getSpy
      .mockResolvedValueOnce({ ...DETAIL, status: 'pending', is_active: false })
      .mockResolvedValueOnce({ ...DETAIL, status: 'active', is_active: true })
    activateSpy.mockResolvedValue({
      id: 'inst-1', code: 'UNICO', name: 'Unico University', status: 'active',
      is_active: true, already_applied: false, message: 'Institution activated.',
    })
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /manage/i }))
    await userEvent.click(await screen.findByRole('button', { name: /approve & activate/i }))
    const dialog = await screen.findByRole('alertdialog', { name: /confirm institution approval/i })
    expect(dialog.textContent).toMatch(/allows its assigned University Admins/i)
    await userEvent.click(within(dialog).getByRole('button', { name: /approve & activate/i }))

    await waitFor(() => expect(activateSpy).toHaveBeenCalledWith('session-token', 'inst-1'))
    expect(screen.queryByRole('button', { name: /^suspend institution$/i })).not.toBeNull()
  })

  it('assigns a university admin by email without asking for a password', async () => {
    listSpy.mockResolvedValue([SUMMARY])
    getSpy.mockResolvedValue(DETAIL)
    assignSpy.mockResolvedValue({
      institution_id: 'inst-1', assigned: true, already_assigned: false,
      admin: { user_id: 'u1', email: 'dean@university.example', institution_id: 'inst-1', scope: 'institution' },
    })
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /manage/i }))
    await userEvent.click(await screen.findByRole('button', { name: /assign university admin/i }))
    await userEvent.type(screen.getByLabelText(/existing account email/i), 'dean@university.example')
    await userEvent.click(screen.getByRole('button', { name: /^assign$/i }))

    await waitFor(() => {
      expect(assignSpy).toHaveBeenCalledWith('session-token', 'inst-1', 'dean@university.example')
    })
    expect(document.querySelector('input[type="password"]')).toBeNull()
  })

  it('labels unimplemented areas as Coming Soon without faking behaviour', async () => {
    listSpy.mockResolvedValue([SUMMARY])
    getSpy.mockResolvedValue(DETAIL)
    render(<InstitutionManagement />, { wrapper: Wrapper })

    await userEvent.click(await screen.findByRole('button', { name: /manage/i }))
    expect(await screen.findByText('Public Knowledge')).toBeDefined()
    expect(await screen.findByText('Platform Information')).toBeDefined()
    expect((await screen.findAllByText(/coming soon/i)).length).toBeGreaterThanOrEqual(3)
  })

  it('surfaces a server failure as an alert instead of silently succeeding', async () => {
    listSpy.mockRejectedValue(new Error('Request failed (FORBIDDEN)'))
    render(<InstitutionManagement />, { wrapper: Wrapper })
    expect(await screen.findByRole('alert')).toBeDefined()
  })
})

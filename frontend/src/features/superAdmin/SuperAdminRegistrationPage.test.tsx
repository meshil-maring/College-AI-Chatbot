import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SuperAdminRegistrationPage from './SuperAdminRegistrationPage.tsx'

const api = vi.hoisted(() => ({ inspect: vi.fn(), register: vi.fn(), recover: vi.fn() }))
vi.mock('../../services/invitations/superAdminInvitationApi.ts', () => ({
  SuperAdminInvitationError: class extends Error { isTerminal = false },
  inspectSuperAdminInvitation: api.inspect, registerSuperAdmin: api.register,
  recoverSuperAdminAccount: api.recover,
}))
const token = 'a'.repeat(64)
const accepted = { email: 'new@example.test', status: 'accepted', expires_at: null, account_recovery_available: true }
beforeEach(() => { vi.resetAllMocks(); api.inspect.mockResolvedValue(accepted) })
afterEach(cleanup)

describe('Super Admin accepted-account recovery', () => {
  it('recovers after reload without password input or a session', async () => {
    api.recover.mockResolvedValue({ message: 'Account ready' })
    const page = render(<SuperAdminRegistrationPage token={token} />)
    await screen.findByRole('button', { name: 'Retry account recovery' })
    page.unmount()
    render(<SuperAdminRegistrationPage token={token} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Retry account recovery' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Account ready')
    expect(api.recover).toHaveBeenCalledExactlyOnceWith(token)
    expect(api.register).not.toHaveBeenCalled()
    expect(screen.queryByLabelText(/^Password$/)).not.toBeInTheDocument()
  })

  it.each(['timeout', 'confirmation failure'])('repairs %s without another registration', async (failure) => {
    api.inspect.mockResolvedValueOnce({ ...accepted, status: 'invited', account_recovery_available: false })
    api.register.mockRejectedValue(new Error(failure))
    api.recover.mockRejectedValueOnce(new Error('confirmation retry failed')).mockResolvedValue({ message: 'Account ready' })
    render(<SuperAdminRegistrationPage token={token} />)
    await userEvent.type(await screen.findByLabelText('First name'), 'Ada')
    await userEvent.type(screen.getByLabelText('Last name'), 'Root')
    await userEvent.type(screen.getByLabelText(/^Password$/), 'correct-horse')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'correct-horse')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Retry account recovery' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry account recovery' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Retry account recovery' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Account ready')
    expect(api.register).toHaveBeenCalledTimes(1)
    expect(api.recover).toHaveBeenCalledTimes(2)
  })
})

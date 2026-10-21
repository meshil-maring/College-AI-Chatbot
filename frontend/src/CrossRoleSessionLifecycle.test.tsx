import './__tests__/CrossRoleSessionLifecycle.support.tsx'
import {
  ME_STAFF,
  SAVED_TOKEN,
  SHELL_MARKERS,
  dispatchStorageEvent,
  reportSessionExpired,
  restoreAs,
} from './__tests__/CrossRoleSessionLifecycle.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import { ACCESS_TOKEN_STORAGE_KEY, REFRESH_TOKEN_STORAGE_KEY } from './features/auth/session/AuthProvider.tsx'
import * as authService from './services/auth/auth.ts'
import { SESSION_EXPIRED_MESSAGE } from './services/shared/sessionEvents.ts'
describe('session restore (refresh) across roles', () => {
  it('restores each role into its own shell from the saved token', async () => {
    for (const role of ['admin', 'staff', 'faculty', 'student'] as const) {
      window.localStorage.clear()
      vi.mocked(authService.fetchCurrentUser).mockReset()
      restoreAs(role)

      const view = render(<App />)
      expect(await screen.findByRole('navigation', { name: SHELL_MARKERS[role] })).toBeInTheDocument()
      // Exactly one shell, exactly one authenticated request (/auth/me).
      for (const other of Object.keys(SHELL_MARKERS)) {
        if (other === role) continue
        expect(screen.queryByRole('navigation', { name: SHELL_MARKERS[other] })).not.toBeInTheDocument()
      }
      expect(authService.fetchCurrentUser).toHaveBeenCalledTimes(1)
      expect(authService.fetchCurrentUser).toHaveBeenCalledWith(SAVED_TOKEN)
      view.unmount()
    }
  })

  it('selects the admin shell and never any other role shell', async () => {
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
  })
})

describe('session expiry across roles', () => {
  it('an admin 401 clears the session, the token, and returns to login', async () => {
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()

    reportSessionExpired(SAVED_TOKEN)

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText(SESSION_EXPIRED_MESSAGE)).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })

  it('a student 401 uses the same single expiry path', async () => {
    restoreAs('student')
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()

    reportSessionExpired(SAVED_TOKEN)

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText(SESSION_EXPIRED_MESSAGE)).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('a 401 naming an already-replaced token cannot clear the current session', async () => {
    restoreAs('admin')
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()

    reportSessionExpired('some-other-token')

    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe(SAVED_TOKEN)
  })
})

describe('logout across roles', () => {
  it('signing out from the admin shell removes the session and the saved token', async () => {
    const user = userEvent.setup()
    restoreAs('admin')
    vi.spyOn(authService, 'revokeSession').mockResolvedValue(undefined)
    render(<App />)
    expect(await screen.findByText('Admin Panel')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByRole('heading', { name: 'College AI Platform' })).toBeInTheDocument()
    expect(authService.revokeSession).toHaveBeenCalledWith(SAVED_TOKEN)
    await waitFor(() => expect(window.localStorage.length).toBe(0))
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    // A deliberate sign-out shows no expiry message.
    expect(screen.queryByText(SESSION_EXPIRED_MESSAGE)).not.toBeInTheDocument()
  })
})

describe('multi-tab session synchronization', () => {
  it('another tab signing out clears this tab (no tab stays authenticated alone)', async () => {
    restoreAs('student')
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()

    dispatchStorageEvent(null)

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('another tab signing in as another role is adopted after /auth/me validation', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'College AI Platform' })).toBeInTheDocument()

    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(ME_STAFF)
    dispatchStorageEvent('other-tab-token')

    expect(await screen.findByRole('navigation', { name: 'Staff navigation' })).toBeInTheDocument()
    expect(authService.fetchCurrentUser).toHaveBeenCalledWith('other-tab-token')
    expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe('other-tab-token')
  })
})

describe('browser storage audit across roles', () => {
  it('persists provider session state, but no role data or credentials', async () => {
    for (const role of ['admin', 'staff', 'faculty', 'student'] as const) {
      window.localStorage.clear()
      window.sessionStorage.clear()
      vi.mocked(authService.fetchCurrentUser).mockReset()
      restoreAs(role)

      const view = render(<App />)
      expect(await screen.findByRole('navigation', { name: SHELL_MARKERS[role] })).toBeInTheDocument()

      expect(window.localStorage.length).toBe(3)
      expect(window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)).toBe('saved-refresh-token')
      expect(window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)).toBe(SAVED_TOKEN)
      // Nothing else is persisted anywhere: no role decision, no dataset.
      expect(window.sessionStorage.length).toBe(0)
      expect(document.body.innerHTML).not.toContain(SAVED_TOKEN)
      expect(screen.queryByText(SAVED_TOKEN)).not.toBeInTheDocument()
      for (let index = 0; index < window.localStorage.length; index += 1) {
        const key = window.localStorage.key(index) ?? ''
        const value = window.localStorage.getItem(key) ?? ''
        expect(value.toLowerCase()).not.toContain('password')
      }

      view.unmount()
    }
  })

  it('removes every trace of the session when the role signs out', async () => {
    const user = userEvent.setup()
    restoreAs('staff')
    vi.spyOn(authService, 'revokeSession').mockResolvedValue(undefined)
    render(<App />)
    expect(await screen.findByRole('navigation', { name: 'Staff navigation' })).toBeInTheDocument()

    const signOutButtons = await screen.findAllByRole('button', { name: 'Sign out' })
    await user.click(signOutButtons[0])

    expect(await screen.findByRole('heading', { name: 'College AI Platform' })).toBeInTheDocument()
    await waitFor(() => {
      expect(window.localStorage.length).toBe(0)
    })
    expect(window.sessionStorage.length).toBe(0)
  })
})

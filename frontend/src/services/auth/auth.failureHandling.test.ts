import './__tests__/auth.support.ts'
import { jsonResponse } from './__tests__/auth.support.ts'
import { describe, expect, it, vi } from 'vitest'
import type { AuthErrorKind } from './auth.ts'
import { AuthError, authErrorMessage, authenticate, fetchCurrentUser, login, studentLogin } from './auth.ts'
import { SESSION_EXPIRED_MESSAGE } from '../shared/sessionEvents.ts'
describe('Phase 6.15.3 critical classification: login 401 ≠ session 401', () => {
  it('classifies the SAME 401 INVALID_CREDENTIALS differently by operation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(401, {
          error: { code: 'INVALID_CREDENTIALS', message: 'Invalid identifier or password' },
        }),
      ),
    )

    const studentErr = await studentLogin({
      identifier: 'REG2026001',
      password: 'wrong',
      institution_code: 'GIT',
    }).catch((e) => e)
    expect(studentErr.kind).toBe<AuthErrorKind>('invalid_credentials')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(401, { error: { code: 'TOKEN_EXPIRED', message: 'Token has expired' } })),
    )

    const sessionErr = await fetchCurrentUser('stale-token').catch((e) => e)
    expect(sessionErr.kind).toBe<AuthErrorKind>('session_invalid')

    // The two are classified differently — the Phase 6.15.1 defect is fixed.
    expect(studentErr.kind).not.toBe(sessionErr.kind)
    expect(authErrorMessage(studentErr)).not.toBe(authErrorMessage(sessionErr))
  })

  it('treats a bare 401 on a login request as invalid credentials', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(401, { detail: 'Unauthorized' })))

    const err = await authenticate('REG2026001', 'wrong', 'GIT').catch((e) => e)
    expect(err.kind).toBe<AuthErrorKind>('invalid_credentials')
  })
})

describe('transport failures', () => {
  it('maps a fetch-level failure to network', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const err = await authenticate('REG2026001', 'secret123', 'GIT').catch((e) => e)
    expect(err).toBeInstanceOf(AuthError)
    expect(err.kind).toBe<AuthErrorKind>('network')
    expect(err.status).toBeNull()
  })

  it('maps a non-envelope 403 to unknown', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(403, { error: { code: 'FORBIDDEN', message: 'no' } })),
    )

    const err = await login({ email: 'a@b.com', password: 'secret123' }).catch((e) => e)
    expect(err.kind).toBe<AuthErrorKind>('unknown')
  })
})

describe('Phase 6.15.6 — one session-expiry vocabulary', () => {
  it('uses the shared session-expiry message for a rejected saved session', () => {
    const error = new AuthError('session_invalid', 401, 'TOKEN_EXPIRED')

    expect(authErrorMessage(error)).toBe(SESSION_EXPIRED_MESSAGE)
    expect(authErrorMessage(error)).toBe('Your session has expired. Please log in again.')
  })

  it('keeps rejected credentials and an expired session clearly distinct', () => {
    const loginError = new AuthError('invalid_credentials', 401, 'INVALID_CREDENTIALS')
    const sessionError = new AuthError('session_invalid', 401, 'TOKEN_EXPIRED')

    expect(authErrorMessage(loginError)).toBe(
      'Invalid login credentials. Please check your details and try again. For help with account approval or access, contact your administrator.',
    )
    expect(authErrorMessage(loginError)).not.toBe(authErrorMessage(sessionError))
  })
})

import './__tests__/auth.support.ts'
import { LOGIN_RESPONSE, jsonResponse, lastCallBody } from './__tests__/auth.support.ts'
import { describe, expect, it, vi } from 'vitest'
import type { AuthErrorKind } from './auth.ts'
import {
  AuthError,
  authErrorMessage,
  authenticate,
  changePassword,
  completePasswordReset,
  fetchCurrentUser,
  login,
  refreshSession,
  requestPasswordRecovery,
  revokeSession,
  studentLogin,
} from './auth.ts'
describe('studentLogin (POST /api/v1/auth/student/login contract)', () => {
  it('maps 5xx to server', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(500, { error: { code: 'INTERNAL_ERROR', message: 'boom' } })),
    )

    const err = await studentLogin({
      identifier: 'REG2026001',
      password: 'secret123',
      institution_code: 'GIT',
    }).catch((e) => e)
    expect(err.kind).toBe<AuthErrorKind>('server')
  })
})

describe('authenticate (unified identifier routing)', () => {
  it('routes an email to the EXISTING general login endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await authenticate('meshil@example.com', 'secret123')

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe('/api/v1/auth/login')
    expect(await lastCallBody(fetchMock)).toEqual({
      email: 'meshil@example.com',
      password: 'secret123',
    })
  })

  it('never sends institution data on the email login path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await authenticate('meshil@example.com', 'secret123', 'GIT')

    expect(await lastCallBody(fetchMock)).toEqual({
      email: 'meshil@example.com',
      password: 'secret123',
    })
  })

  it('routes a register number to the student endpoint with the institution code', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await authenticate('REG2026001', 'secret123', 'GIT')

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe('/api/v1/auth/student/login')
    expect(await lastCallBody(fetchMock)).toEqual({
      identifier: 'REG2026001',
      password: 'secret123',
      institution_code: 'GIT',
    })
  })

  it('routes a university roll number to the student endpoint with the institution code', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await authenticate('UNI20260001', 'secret123', 'IMPHAL')

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe('/api/v1/auth/student/login')
    expect(await lastCallBody(fetchMock)).toEqual({
      identifier: 'UNI20260001',
      password: 'secret123',
      institution_code: 'IMPHAL',
    })
  })

  it('trims surrounding whitespace from the identifier', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await authenticate('  meshil@example.com  ', 'secret123')

    expect(await lastCallBody(fetchMock)).toEqual({
      email: 'meshil@example.com',
      password: 'secret123',
    })
  })
})

describe('password and session lifecycle endpoints', () => {
  it('requests provider-managed recovery without sending a new password', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { message: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)

    await requestPasswordRecovery('person@college.edu')

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/auth/forgot-password')
    expect(JSON.parse(String(init.body))).toEqual({ email: 'person@college.edu' })
  })

  it('sends recovery credentials through the bearer header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { message: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)

    await completePasswordReset('recovery-token', 'new-password-123', 'new-password-123')

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/auth/reset-password')
    expect((init.headers as Record<string, string>).Authorization).toContain('Bearer')
    expect(JSON.parse(String(init.body))).toEqual({
      new_password: 'new-password-123',
      confirm_password: 'new-password-123',
    })
  })

  it('sends current and new passwords only to the authenticated change endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { message: 'ok' }))
    vi.stubGlobal('fetch', fetchMock)

    await changePassword('access-token', 'old-password', 'new-password', 'new-password')

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/auth/change-password')
    expect((init.headers as Record<string, string>).Authorization).toContain('Bearer')
    expect(JSON.parse(String(init.body))).toEqual({
      current_password: 'old-password',
      new_password: 'new-password',
      confirm_password: 'new-password',
    })
  })

  it('renews with the provider refresh token and supports scoped logout', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, LOGIN_RESPONSE))
      .mockResolvedValueOnce(jsonResponse(200, { message: 'revoked' }))
      .mockResolvedValueOnce(jsonResponse(200, { message: 'revoked' }))
    vi.stubGlobal('fetch', fetchMock)

    await refreshSession('provider-refresh-token')
    await revokeSession('access-token')
    await revokeSession('access-token', true)

    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/auth/refresh')
    expect(JSON.parse(String((fetchMock.mock.calls[0]?.[1] as RequestInit).body))).toEqual({
      refresh_token: 'provider-refresh-token',
    })
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/v1/auth/logout')
    expect(fetchMock.mock.calls[2]?.[0]).toBe('/api/v1/auth/logout-all')
  })
})

describe('fetchCurrentUser (GET /api/v1/auth/me session operation)', () => {
  it('explains ACCOUNT_INACTIVE only when validating an existing session', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() =>
        Promise.resolve(
          jsonResponse(403, {
            error: { code: 'ACCOUNT_INACTIVE', message: 'private backend details' },
          }),
        ),
      ),
    )
    const sessionError = await fetchCurrentUser('synthetic-token').catch((error) => error)
    expect(sessionError).toMatchObject({ kind: 'account_inactive', status: 403, code: 'ACCOUNT_INACTIVE' })
    expect(authErrorMessage(sessionError)).toBe(
      'Your account is inactive. Contact your institution administrator for help with access.',
    )
    const loginError = await login({ email: 'fixture@example.test', password: 'secret123' }).catch((error) => error)
    expect(loginError.kind).toBe('unknown')
    expect(authErrorMessage(loginError)).not.toMatch(/inactive|private backend details/)
  })

  it('parses the identity and sends the bearer token', async () => {
    const me = {
      authenticated: true,
      user_id: '90000000-0000-0000-0000-000000000001',
      auth_user_id: '71000000-0000-0000-0000-000000000001',
      email: 'meshil@example.com',
    }
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, me))
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchCurrentUser('test-access-token')

    expect(result).toEqual(me)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/auth/me')
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-access-token')
  })

  it('maps 401 TOKEN_EXPIRED on /auth/me to session_invalid', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(401, { error: { code: 'TOKEN_EXPIRED', message: 'Token has expired' } })),
    )

    const err = await fetchCurrentUser('expired-token').catch((e) => e)
    expect(err).toBeInstanceOf(AuthError)
    expect(err.kind).toBe<AuthErrorKind>('session_invalid')
    expect(err.status).toBe(401)
  })

  it('maps 404 USER_NOT_FOUND on /auth/me to session_invalid', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(404, { error: { code: 'USER_NOT_FOUND', message: 'no user' } })),
    )

    const err = await fetchCurrentUser('token').catch((e) => e)
    expect(err.kind).toBe<AuthErrorKind>('session_invalid')
  })
})

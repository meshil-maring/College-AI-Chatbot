/**
 * Phase 6.15.3 — Authentication service tests (student identifier login).
 *
 * Verifies the HTTP boundary: request URLs/methods/bodies for BOTH login
 * endpoints, identifier routing, and classification of backend AppError
 * envelopes into typed, user-safe AuthError kinds (using the real error
 * CODES, never string parsing).
 *
 * Critical contract under test: the student login endpoint returns HTTP 401
 * `INVALID_CREDENTIALS` for rejected credentials, which must be classified as
 * `invalid_credentials` — NOT as `session_invalid` (which is reserved for
 * 401/404 on the /auth/me session operation).
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AuthError,
  authenticate,
  authErrorMessage,
  fetchCurrentUser,
  isEmailAddress,
  login,
  studentLogin,
} from './auth.ts'
import type { AuthErrorKind } from './auth.ts'
import { SESSION_EXPIRED_MESSAGE } from './sessionEvents.ts'

const LOGIN_RESPONSE = {
  access_token: 'test-access-token',
  message: 'Login successful.',
  user: { id: '71000000-0000-0000-0000-000000000001', email: 'meshil@example.com' },
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function lastCallBody(fetchMock: ReturnType<typeof vi.fn>): Promise<unknown> {
  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
  return JSON.parse(String(init.body))
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

describe('isEmailAddress (backend `_is_email` mirror)', () => {
  it('classifies emails', () => {
    expect(isEmailAddress('meshil@example.com')).toBe(true)
    expect(isEmailAddress('  meshil@example.com ')).toBe(true)
  })

  it('classifies academic identifiers as non-emails', () => {
    expect(isEmailAddress('REG2026001')).toBe(false)
    expect(isEmailAddress('UNI20260001')).toBe(false)
  })

  it('matches the backend heuristic for "@" without a dotted domain', () => {
    // The backend heuristic requires a dot in the domain part.
    expect(isEmailAddress('user@localhost')).toBe(false)
  })
})

describe('login (existing POST /api/v1/auth/login contract)', () => {
  it('sends email + password to the general login endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    const result = await login({ email: 'meshil@example.com', password: 'secret123' })

    expect(result).toEqual(LOGIN_RESPONSE)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/auth/login')
    expect(init.method).toBe('POST')
    expect(await lastCallBody(fetchMock)).toEqual({
      email: 'meshil@example.com',
      password: 'secret123',
    })
  })

  it('maps 400 INVALID_CREDENTIALS to invalid_credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(400, {
          error: { code: 'INVALID_CREDENTIALS', message: 'Invalid login credentials' },
        }),
      ),
    )

    const err = await login({ email: 'a@b.com', password: 'wrong' }).catch((e) => e)
    expect(err).toBeInstanceOf(AuthError)
    expect(err.kind).toBe<AuthErrorKind>('invalid_credentials')
    expect(err.status).toBe(400)
  })
})

describe('studentLogin (POST /api/v1/auth/student/login contract)', () => {
  it('sends identifier + institution_code + password for a register number', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    const result = await studentLogin({
      identifier: 'REG2026001',
      password: 'secret123',
      institution_code: 'GIT',
    })

    expect(result).toEqual(LOGIN_RESPONSE)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/auth/student/login')
    expect(init.method).toBe('POST')
    expect(await lastCallBody(fetchMock)).toEqual({
      identifier: 'REG2026001',
      password: 'secret123',
      institution_code: 'GIT',
    })
  })

  it('sends identifier + institution_code + password for a roll number', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await studentLogin({
      identifier: 'UNI20260001',
      password: 'secret123',
      institution_code: 'IMPHAL',
    })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe('/api/v1/auth/student/login')
    expect(await lastCallBody(fetchMock)).toEqual({
      identifier: 'UNI20260001',
      password: 'secret123',
      institution_code: 'IMPHAL',
    })
  })

  it('sends NO institution_code for an email identifier (backend ignores it)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, LOGIN_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    await studentLogin({ identifier: 'meshil@example.com', password: 'secret123' })

    expect(await lastCallBody(fetchMock)).toEqual({
      identifier: 'meshil@example.com',
      password: 'secret123',
    })
  })

  it('maps HTTP 401 INVALID_CREDENTIALS to invalid_credentials (NOT session_invalid)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(401, {
          error: { code: 'INVALID_CREDENTIALS', message: 'Invalid identifier or password' },
        }),
      ),
    )

    const err = await studentLogin({
      identifier: 'REG2026001',
      password: 'wrong',
      institution_code: 'GIT',
    }).catch((e) => e)
    expect(err).toBeInstanceOf(AuthError)
    expect(err.kind).toBe<AuthErrorKind>('invalid_credentials')
    expect(err.status).toBe(401)
    expect(err.code).toBe('INVALID_CREDENTIALS')
    expect(authErrorMessage(err)).toBe(
      'Invalid login credentials. Please check your details and try again.',
    )
  })

  it('maps a 422 (missing institution_code) to validation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'institution_code is required for academic identifier login',
          },
        }),
      ),
    )

    const err = await studentLogin({ identifier: 'REG2026001', password: 'secret123' }).catch(
      (e) => e,
    )
    expect(err.kind).toBe<AuthErrorKind>('validation')
    expect(err.status).toBe(422)
  })

  it('maps 5xx to server', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(500, { error: { code: 'INTERNAL_ERROR', message: 'boom' } }),
      ),
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

describe('fetchCurrentUser (GET /api/v1/auth/me session operation)', () => {
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
    expect((init.headers as Record<string, string>).Authorization).toBe(
      'Bearer test-access-token',
    )
  })

  it('maps 401 TOKEN_EXPIRED on /auth/me to session_invalid', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(401, { error: { code: 'TOKEN_EXPIRED', message: 'Token has expired' } }),
      ),
    )

    const err = await fetchCurrentUser('expired-token').catch((e) => e)
    expect(err).toBeInstanceOf(AuthError)
    expect(err.kind).toBe<AuthErrorKind>('session_invalid')
    expect(err.status).toBe(401)
  })

  it('maps 404 USER_NOT_FOUND on /auth/me to session_invalid', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(404, { error: { code: 'USER_NOT_FOUND', message: 'no user' } }),
      ),
    )

    const err = await fetchCurrentUser('token').catch((e) => e)
    expect(err.kind).toBe<AuthErrorKind>('session_invalid')
  })
})

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
      vi.fn().mockResolvedValue(
        jsonResponse(401, { error: { code: 'TOKEN_EXPIRED', message: 'Token has expired' } }),
      ),
    )

    const sessionErr = await fetchCurrentUser('stale-token').catch((e) => e)
    expect(sessionErr.kind).toBe<AuthErrorKind>('session_invalid')

    // The two are classified differently — the Phase 6.15.1 defect is fixed.
    expect(studentErr.kind).not.toBe(sessionErr.kind)
    expect(authErrorMessage(studentErr)).not.toBe(authErrorMessage(sessionErr))
  })

  it('treats a bare 401 on a login request as invalid credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(401, { detail: 'Unauthorized' })),
    )

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
      'Invalid login credentials. Please check your details and try again.',
    )
    expect(authErrorMessage(loginError)).not.toBe(authErrorMessage(sessionError))
  })
})
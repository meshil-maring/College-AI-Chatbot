import './__tests__/auth.support.ts'
import { LOGIN_RESPONSE, jsonResponse, lastCallBody } from './__tests__/auth.support.ts'
import { describe, expect, it, vi } from 'vitest'
import type { AuthErrorKind } from './auth.ts'
import { AuthError, authErrorMessage, isEmailAddress, login, studentLogin } from './auth.ts'
;('isEmailAddress (backend `_is_email` mirror)',
  () => {
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
  it.each(['AUTH_SERVICE_UNAVAILABLE', 'AUTH_AUDIT_UNAVAILABLE'])(
    'explains %s without exposing backend diagnostics or blaming credentials',
    async (code) => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          jsonResponse(503, {
            error: { code, message: 'private database hostname and credentials' },
          }),
        ),
      )

      const error = await login({ email: 'admin@college.edu', password: 'test-password' }).catch((value) => value)
      expect(error).toBeInstanceOf(AuthError)
      expect(error.kind).toBe('unavailable')
      expect(error.status).toBe(503)
      expect(authErrorMessage(error)).toBe('Authentication is temporarily unavailable. Please try again shortly.')
      expect(error.message).not.toContain('private database')
    },
  )

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

  it('shows a clear message for a verified faculty login that is still pending', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(403, {
          error: { code: 'REGISTRATION_PENDING', message: 'Registration pending' },
        }),
      ),
    )

    const err = await login({ email: 'faculty@example.com', password: 'secret123' }).catch((e) => e)
    expect(err).toBeInstanceOf(AuthError)
    expect(err.kind).toBe<AuthErrorKind>('registration_pending')
    expect(authErrorMessage(err)).toBe(
      'Your registration is pending. You can sign in after your institution approves it. Contact your institution administrator if you need help.',
    )
  })
})

describe('studentLogin (POST /api/v1/auth/student/login contract)', () => {
  it.each(['pending', 'rejected', 'inactive'])(
    'keeps %s account details out of the login error while offering account-access help',
    async (state) => {
      const rawMessage = `Synthetic account is ${state}`
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          jsonResponse(401, {
            error: { code: 'INVALID_CREDENTIALS', message: rawMessage },
          }),
        ),
      )
      const error = await studentLogin({
        identifier: 'TEST1001',
        institution_code: 'TEST',
        password: 'test-password',
      }).catch((value) => value)
      expect(error).toBeInstanceOf(AuthError)
      expect(error.kind).toBe('invalid_credentials')
      expect(error.message).toBe(
        'Invalid login credentials. Please check your details and try again. For help with account approval or access, contact your administrator.',
      )
      expect(authErrorMessage(error)).toBe(error.message)
      expect(error.message).not.toContain(rawMessage)
      expect(error.message).not.toContain(state)
    },
  )

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
      'Invalid login credentials. Please check your details and try again. For help with account approval or access, contact your administrator.',
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

    const err = await studentLogin({ identifier: 'REG2026001', password: 'secret123' }).catch((e) => e)
    expect(err.kind).toBe<AuthErrorKind>('validation')
    expect(err.status).toBe(422)
  })
})

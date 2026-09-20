/**
 * Phase 6.15.2 — Registration service client tests.
 *
 * Verifies the HTTP boundary: request URLs/methods/bodies, response parsing,
 * and classification of backend AppError envelopes into typed, user-safe
 * RegistrationError kinds (using the real error CODES, never string parsing).
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  RegistrationError,
  lookupInstitution,
  registerStudent,
  registrationErrorMessage,
} from './registration.ts'
import type { RegistrationErrorKind } from './registration.ts'

const INSTITUTION = {
  institution_id: 'b0000000-0000-0000-0000-0000000000a1',
  code: 'IMPHAL',
  name: 'Imphal College',
}

const REGISTRATION_RESPONSE = {
  message: 'Student registration submitted.',
  user_id: '71000000-0000-0000-0000-000000000001',
  institution_id: INSTITUTION.institution_id,
  institution_code: 'IMPHAL',
  registration_type: 'student',
  approval_status: 'pending',
  student_id: '30000000-0000-0000-0000-000000000151',
  request_id: null,
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

describe('lookupInstitution', () => {
  it('sends the code as a query parameter and parses the safe response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, INSTITUTION))
    vi.stubGlobal('fetch', fetchMock)

    const result = await lookupInstitution('IMPHAL')

    expect(result).toEqual(INSTITUTION)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/institutions/lookup?code=IMPHAL')
    expect(init.method).toBe('GET')
  })

  it('URL-encodes special characters in the code', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, INSTITUTION))
    vi.stubGlobal('fetch', fetchMock)

    await lookupInstitution('A B/1')

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe('/api/v1/institutions/lookup?code=A%20B%2F1')
  })

  it('maps a 404 envelope to the institution_not_found kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(404, {
          error: { code: 'INSTITUTION_NOT_FOUND', message: 'Institution not found' },
        }),
      ),
    )

    const err = await lookupInstitution('NOPE99').catch((e) => e)
    expect(err).toBeInstanceOf(RegistrationError)
    expect(err.kind).toBe<RegistrationErrorKind>('institution_not_found')
    expect(registrationErrorMessage(err)).toBe(
      'Institution code was not found. Please check the code and try again.',
    )
  })

  it('maps a 403 envelope to the institution_not_accepting kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(403, {
          error: {
            code: 'INSTITUTION_NOT_ACCEPTING_REGISTRATIONS',
            message: 'not accepting',
          },
        }),
      ),
    )

    const err = await lookupInstitution('IMPHAL').catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('institution_not_accepting')
    expect(registrationErrorMessage(err)).toBe(
      'This institution is not currently accepting registrations.',
    )
  })

  it('maps a 422 envelope to the validation kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          error: { code: 'VALIDATION_ERROR', message: 'Request validation failed' },
        }),
      ),
    )

    const err = await lookupInstitution('A').catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('validation')
  })

  it('maps fetch rejection to the network kind', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const err = await lookupInstitution('IMPHAL').catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('network')
  })

  it('maps an abort signal to the timeout kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockRejectedValue(new DOMException('The operation was aborted.', 'AbortError')),
    )

    const err = await lookupInstitution('IMPHAL').catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('timeout')
    expect(registrationErrorMessage(err)).toBe('The request timed out. Please try again.')
  })

  it('maps a 500 response to the server kind', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(500, {})))

    const err = await lookupInstitution('IMPHAL').catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('server')
  })
})

describe('registerStudent', () => {
  it('posts the exact backend registration schema', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(201, REGISTRATION_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    const request = {
      registration_type: 'student' as const,
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'secret123',
      first_name: 'Jane',
      last_name: 'Doe',
      register_number: '1001',
      university_roll_number: null,
    }
    const result = await registerStudent(request)

    expect(result).toEqual(REGISTRATION_RESPONSE)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/users/register')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual(request)
  })

  it('maps duplicate-email codes to the email kind', async () => {
    for (const code of ['EMAIL_ALREADY_REGISTERED', 'STUDENT_ALREADY_REGISTERED']) {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(jsonResponse(409, { error: { code, message: 'dup' } })),
      )
      const err = await registerStudent({
        registration_type: 'student',
        institution_code: 'IMPHAL',
        email: 'jane@example.com',
        password: 'secret123',
        first_name: 'Jane',
        last_name: 'Doe',
      }).catch((e) => e)
      expect(err.kind).toBe<RegistrationErrorKind>('email_already_registered')
      expect(registrationErrorMessage(err)).toBe(
        'An account with this email already exists.',
      )
    }
  })

  it('maps duplicate register-number codes to its kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(409, {
          error: {
            code: 'REGISTER_NUMBER_ALREADY_REGISTERED',
            message: 'dup',
          },
        }),
      ),
    )
    const err = await registerStudent({
      registration_type: 'student',
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'secret123',
      first_name: 'Jane',
      last_name: 'Doe',
      register_number: '1001',
    }).catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('register_number_already_registered')
    expect(registrationErrorMessage(err)).toBe(
      'This register number is already registered.',
    )
  })

  it('maps duplicate roll-number codes to its kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(409, {
          error: {
            code: 'ROLL_NUMBER_ALREADY_REGISTERED',
            message: 'dup',
          },
        }),
      ),
    )
    const err = await registerStudent({
      registration_type: 'student',
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'secret123',
      first_name: 'Jane',
      last_name: 'Doe',
      university_roll_number: '2026-1001',
    }).catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('roll_number_already_registered')
    expect(registrationErrorMessage(err)).toBe(
      'This university roll number is already registered.',
    )
  })

  it('maps 422 envelopes to the validation kind', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Request validation failed',
            details: [],
          },
        }),
      ),
    )
    const err = await registerStudent({
      registration_type: 'student',
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'secret123',
      first_name: 'Jane',
      last_name: 'Doe',
    }).catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('validation')
  })

  it('maps fetch rejection to the network kind', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const err = await registerStudent({
      registration_type: 'student',
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'secret123',
      first_name: 'Jane',
      last_name: 'Doe',
    }).catch((e) => e)
    expect(err.kind).toBe<RegistrationErrorKind>('network')
  })

  it('does not leak the password into the error message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const err = await registerStudent({
      registration_type: 'student',
      institution_code: 'IMPHAL',
      email: 'jane@example.com',
      password: 'super-secret-value',
      first_name: 'Jane',
      last_name: 'Doe',
    }).catch((e) => e)
    expect(err.message).not.toContain('super-secret-value')
  })
})

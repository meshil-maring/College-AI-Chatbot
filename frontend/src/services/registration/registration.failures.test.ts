import './__tests__/registration.support.ts'
import { jsonResponse } from './__tests__/registration.support.ts'
import { expect, it, vi } from 'vitest'
import type { RegistrationErrorKind } from './registration.ts'
import { registerStudent } from './registration.ts'
describe('registerStudent', () => {
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

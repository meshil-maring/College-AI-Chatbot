/**
 * DEVELOPMENT / TESTING ONLY — tests for the dev-only password recovery
 * service client (services/devAuth.ts).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DevAuthError,
  devChangePassword,
  devForgotPassword,
  fetchDevAuthStatus,
} from './devAuth.ts'

describe('devAuth', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetchDevAuthStatus returns disabled when backend reports dev_test_mode=false', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ dev_test_mode: false }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const result = await fetchDevAuthStatus()
    expect(result.dev_test_mode).toBe(false)
  })

  it('fetchDevAuthStatus returns enabled when backend reports dev_test_mode=true', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ dev_test_mode: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const result = await fetchDevAuthStatus()
    expect(result.dev_test_mode).toBe(true)
  })

  it('fetchDevAuthStatus fails closed (disabled) on network error', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockRejectedValueOnce(new TypeError('network down'))
    const result = await fetchDevAuthStatus()
    expect(result.dev_test_mode).toBe(false)
  })

  it('devForgotPassword resolves on success', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'Password reset successfully. (DEV/TEST ONLY)' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const result = await devForgotPassword({
      email: 'student@college.edu',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    })
    expect(result.message).toContain('successfully')
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/dev/auth/forgot-password')
    expect(options.method).toBe('POST')
  })

  it('devForgotPassword throws a "disabled" DevAuthError when the feature flag is off', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Not found' } }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      }),
    )
    await expect(
      devForgotPassword({
        email: 'student@college.edu',
        new_password: 'newpass123',
        confirm_password: 'newpass123',
      }),
    ).rejects.toMatchObject({ kind: 'disabled' } satisfies Partial<DevAuthError>)
  })

  it('devForgotPassword throws "user_not_found" for unknown email', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: 'USER_NOT_FOUND', message: 'not found' } }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      }),
    )
    await expect(
      devForgotPassword({
        email: 'nobody@college.edu',
        new_password: 'newpass123',
        confirm_password: 'newpass123',
      }),
    ).rejects.toMatchObject({ kind: 'user_not_found' })
  })

  it('devChangePassword throws "invalid_credentials" on wrong current password', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: 'INVALID_CREDENTIALS', message: 'bad' } }), {
        status: 400,
        headers: { 'content-type': 'application/json' },
      }),
    )
    await expect(
      devChangePassword({
        email: 'student@college.edu',
        current_password: 'wrong',
        new_password: 'newpass123',
        confirm_password: 'newpass123',
      }),
    ).rejects.toMatchObject({ kind: 'invalid_credentials' })
  })

  it('devChangePassword resolves on success', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'Password changed successfully. (DEV/TEST ONLY)' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const result = await devChangePassword({
      email: 'student@college.edu',
      current_password: 'oldpass123',
      new_password: 'newpass123',
      confirm_password: 'newpass123',
    })
    expect(result.message).toContain('successfully')
  })
})

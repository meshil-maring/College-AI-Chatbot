/// <reference types="vitest/globals" />
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPlatformIdentity, PlatformAuthorizationError } from './platformApi.ts'

afterEach(() => vi.unstubAllGlobals())

describe('platform authorization API', () => {
  it('sends the session token only in the authorization header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ role: 'super_admin', scope: 'platform' }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)
    await expect(getPlatformIdentity('opaque-token')).resolves.toEqual({
      role: 'super_admin', scope: 'platform',
    })
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/platform/me', {
      method: 'GET', headers: { Authorization: 'Bearer opaque-token' },
    })
    expect(fetchMock.mock.calls[0][0]).not.toContain('opaque-token')
  })

  it('fails closed on forbidden and malformed responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 403 })))
    await expect(getPlatformIdentity('token')).rejects.toMatchObject<Partial<PlatformAuthorizationError>>({ status: 403 })

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ role: 'admin', scope: 'institution' }), { status: 200 },
    )))
    await expect(getPlatformIdentity('token')).rejects.toMatchObject<Partial<PlatformAuthorizationError>>({ status: 500 })
  })
})


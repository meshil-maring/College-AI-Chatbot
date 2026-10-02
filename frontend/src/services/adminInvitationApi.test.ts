/// <reference types="vitest/globals" />
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  AdminInvitationError,
  acceptInvitation,
  inspectInvitation,
} from './adminInvitationApi.ts'

const BASE = '/api/v1/admin-invitations'
const TOKEN = 'a'.repeat(64)

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function errorResponse(status: number, code: string, message: string): Response {
  return jsonResponse({ error: { code, message } }, status)
}

afterEach(() => vi.unstubAllGlobals())

describe('admin invitation API client', () => {
  it('sends NO authorization header, because the invited person has no session', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      status: 'invited',
      institution_name: 'Unico University',
      institution_code: 'UNICO',
      email: 'dean@unico.example',
      expires_at: '2099-01-01T00:00:00+00:00',
    }))
    vi.stubGlobal('fetch', fetchMock)

    await inspectInvitation(TOKEN)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${BASE}/${TOKEN}`)
    expect(init.method).toBe('GET')
    // No session token is invented, and the password is never involved here.
    expect(init.headers).toEqual({})
    expect(init.body).toBeUndefined()
  })

  it('url-encodes the opaque token rather than interpolating it raw', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'invited' }))
    vi.stubGlobal('fetch', fetchMock)

    await inspectInvitation('token/with/slashes')

    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/token%2Fwith%2Fslashes`)
  })

  it('posts only the password fields on acceptance', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      institution_id: 'i1',
      institution_name: 'Unico University',
      email: 'dean@unico.example',
      role: 'admin',
      scope: 'institution',
      message: 'ok',
    }, 201))
    vi.stubGlobal('fetch', fetchMock)

    await acceptInvitation(TOKEN, { password: 'correct-horse-battery' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${BASE}/${TOKEN}/accept`)
    expect(init.method).toBe('POST')
    // The body carries credentials only: no role, institution, scope or token.
    expect(JSON.parse(init.body as string)).toEqual({ password: 'correct-horse-battery' })
  })

  it.each([
    ['INVITATION_EXPIRED', 410],
    ['INVITATION_CANCELLED', 410],
    ['INVITATION_ALREADY_ACCEPTED', 410],
    ['INVITATION_INVALID', 400],
  ])('surfaces %s as a safe typed error', async (code, status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      errorResponse(status, code, 'This invitation cannot be used.'),
    ))

    await expect(inspectInvitation(TOKEN)).rejects.toBeInstanceOf(AdminInvitationError)
  })

  it('marks an expired/cancelled/consumed invitation as terminal', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      errorResponse(410, 'INVITATION_EXPIRED', 'This invitation has expired.'),
    ))

    const error = await acceptInvitation(TOKEN, { password: 'x'.repeat(10) }).catch(
      (err: unknown) => err,
    )

    expect(error).toBeInstanceOf(AdminInvitationError)
    expect((error as AdminInvitationError).isTerminal).toBe(true)
    expect((error as AdminInvitationError).message).toBe('This invitation has expired.')
  })

  it('does not treat a transient failure as terminal', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      errorResponse(500, 'INVITATION_ACCEPTANCE_FAILED', 'Please try again.'),
    ))

    const error = await acceptInvitation(TOKEN, { password: 'x'.repeat(10) }).catch(
      (err: unknown) => err,
    )

    expect((error as AdminInvitationError).isTerminal).toBe(false)
  })

  it('reports a network failure without leaking internals', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('boom')))

    const error = await inspectInvitation(TOKEN).catch((err: unknown) => err)

    expect(error).toBeInstanceOf(AdminInvitationError)
    expect((error as AdminInvitationError).message).toBe(
      'Could not reach the backend. Please try again.',
    )
  })

  it('falls back to a status message for a non-JSON error body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('<html>gateway</html>', { status: 502 }),
    ))

    const error = await inspectInvitation(TOKEN).catch((err: unknown) => err)

    expect((error as AdminInvitationError).message).toBe('Request failed with HTTP 502')
  })
})
/// <reference types="vitest/globals" />
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  PlatformInstitutionError,
  activateInstitution,
  assignInstitutionAdmin,
  createInstitution,
  getInstitution,
  listInstitutions,
  suspendInstitution,
  updateInstitution,
} from './platformInstitutionsApi.ts'

const BASE = '/api/v1/platform/institutions'
const ID = '40000000-0000-0000-0000-000000000001'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('platform institution API client', () => {
  it('sends the token only in the authorization header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ institutions: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await listInstitutions('opaque-token')

    expect(fetchMock).toHaveBeenCalledWith(BASE, {
      method: 'GET',
      headers: { Authorization: 'Bearer opaque-token' },
      body: undefined,
    })
    // The credential must never appear in the request URL.
    expect(fetchMock.mock.calls[0][0]).not.toContain('opaque-token')
  })

  it('unwraps the institution list envelope', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({
      institutions: [
        { id: ID, code: 'UNICO', name: 'Unico University', status: 'active', is_active: true, admin_count: 2 },
      ],
    })))

    await expect(listInstitutions('t')).resolves.toEqual([
      { id: ID, code: 'UNICO', name: 'Unico University', status: 'active', is_active: true, admin_count: 2 },
    ])
  })

  it('posts create payloads to the collection endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: ID }, 201))
    vi.stubGlobal('fetch', fetchMock)

    await createInstitution('t', { name: 'Unico University', code: 'UNICO' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(BASE)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ name: 'Unico University', code: 'UNICO' })
  })

  it('uses lifecycle sub-resources rather than a status field on PATCH', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(jsonResponse({ id: ID })),
    )
    vi.stubGlobal('fetch', fetchMock)

    await suspendInstitution('t', ID)
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/${ID}/suspend`)

    await activateInstitution('t', ID)
    expect(fetchMock.mock.calls[1][0]).toBe(`${BASE}/${ID}/activate`)
  })

  it('encodes the institution id in the path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: ID }))
    vi.stubGlobal('fetch', fetchMock)
    await getInstitution('t', 'a b/c')
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/a%20b%2Fc`)
  })

  it('sends only an email when assigning an admin and never a password', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ assigned: true }, 201))
    vi.stubGlobal('fetch', fetchMock)

    await assignInstitutionAdmin('t', ID, 'dean@university.example')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${BASE}/${ID}/admins`)
    expect(JSON.parse(init.body)).toEqual({ email: 'dean@university.example' })
    expect(init.body).not.toMatch(/password/i)
  })

  it('surfaces the server error code and message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(
      { error: { code: 'INSTITUTION_CODE_TAKEN', message: 'This institution code is already taken' } },
      409,
    )))

    await expect(createInstitution('t', { name: 'X', code: 'X' })).rejects.toMatchObject<Partial<PlatformInstitutionError>>({
      status: 409,
      code: 'INSTITUTION_CODE_TAKEN',
      message: 'This institution code is already taken',
    })
  })

  it('fails closed on a forbidden response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(
      { error: { code: 'FORBIDDEN', message: 'You do not have permission to perform this action' } },
      403,
    )))
    await expect(listInstitutions('t')).rejects.toMatchObject<Partial<PlatformInstitutionError>>({ status: 403 })
  })

  it('reports a network failure without leaking internals', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED 127.0.0.1:54321')))
    await expect(listInstitutions('t')).rejects.toMatchObject<Partial<PlatformInstitutionError>>({ status: 0 })
  })

  it('sends only supplied fields on a partial update', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: ID }))
    vi.stubGlobal('fetch', fetchMock)

    await updateInstitution('t', ID, { name: 'Renamed' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${BASE}/${ID}`)
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ name: 'Renamed' })
  })
})

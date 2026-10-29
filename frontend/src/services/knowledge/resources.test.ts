import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from './resources.ts'
import type { ResourceFields, ResourceRevision } from '../../types/learningResources.ts'
import { onSessionExpired, resetSessionExpiredListeners } from '../shared/sessionEvents.ts'

const revision = {
  revision_id: 'revision/a',
  knowledge_source_id: 'source/a',
  revision_version: 7,
  policy_version: 3,
} as ResourceRevision
afterEach(() => {
  vi.unstubAllGlobals()
  resetSessionExpiredListeners()
})
function transport() {
  const send = vi
    .fn()
    .mockResolvedValue(new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }))
  vi.stubGlobal('fetch', send)
  return send
}
describe('shared learning resource transport', () => {
  it('uses bounded backend pagination and forwards read cancellation', async () => {
    const send = transport()
    const controller = new AbortController()
    await api.listResources('private-token', 'review', 20, controller.signal)
    expect(send).toHaveBeenCalledWith(
      '/api/v1/knowledge/revisions?view=review&limit=20&offset=20',
      expect.objectContaining({
        method: 'GET',
        signal: controller.signal,
        headers: { Authorization: 'Bearer private-token' },
      }),
    )
  })
  it('sends draft fields and the expected revision token without a tenant override', async () => {
    const send = transport()
    const fields: ResourceFields = {
      title: 'Guide',
      source_type: 'handbook',
      description: null,
      audience: { mode: 'roles', roles: ['student', 'faculty'] },
      effective_from: null,
      effective_until: null,
    }
    await api.saveRevision('token', revision, fields, 6)
    expect(send.mock.calls[0][0]).toBe('/api/v1/knowledge/resources/source%2Fa/revisions/revision%2Fa')
    expect(JSON.parse(send.mock.calls[0][1].body)).toEqual({ ...fields, expected_version: 6 })
  })
  it('uploads multipart data with a revision token and optional replacement document', async () => {
    const send = transport()
    const file = new File(['Fictional resource'], 'guide.txt', { type: 'text/plain' })
    await api.uploadResourceFile('token', revision, file, 'document-a')
    const options = send.mock.calls[0][1]
    expect(options.headers).toEqual({ Authorization: 'Bearer token' })
    expect(options.body.get('file')).toBe(file)
    expect(options.body.get('expected_version')).toBe('7')
    expect(options.body.get('document_id')).toBe('document-a')
  })
  it('publishes the exact revision and live policy tokens', async () => {
    const send = transport()
    await api.decideRevision('token', revision, 'publish', '  Reviewed  ')
    expect(send.mock.calls[0][0]).toBe('/api/v1/knowledge/revisions/revision%2Fa/publish')
    expect(JSON.parse(send.mock.calls[0][1].body)).toEqual({
      expected_version: 7,
      expected_policy: 3,
      notes: 'Reviewed',
    })
  })
  it('retains server error codes and sends token-scoped session expiry', async () => {
    const listener = vi.fn()
    onSessionExpired(listener)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: 'TOKEN_EXPIRED', message: 'Expired' } }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    )
    await expect(api.getRevision('retired-token', 'revision-a')).rejects.toMatchObject({
      status: 401,
      code: 'TOKEN_EXPIRED',
    })
    expect(listener).toHaveBeenCalledWith('retired-token')
  })
  it('preserves abort errors and does not misreport them as network failures', async () => {
    const controller = new AbortController()
    controller.abort()
    const error = new DOMException('Aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
    await expect(api.listResources('token', 'library', 0, controller.signal)).rejects.toBe(error)
  })
})

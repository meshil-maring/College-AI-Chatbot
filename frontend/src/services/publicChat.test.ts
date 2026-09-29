import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PublicChatError, publicChat } from './publicChat.ts'

describe('publicChat client', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()))
  afterEach(() => vi.unstubAllGlobals())

  it('posts only the narrow public contract without authorization', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      answer: 'Admissions open in June.',
      status: 'success',
      sources: [{ title: 'Admission FAQ', section: null, quote: 'Applications open in June.' }],
    }), { status: 200, headers: { 'content-type': 'application/json' } }))

    await publicChat({ institution_code: 'GIT', message: 'When do admissions open?' })

    const [url, options] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/chat/public')
    expect(options.method).toBe('POST')
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(options.body as string)).toEqual({
      institution_code: 'GIT',
      message: 'When do admissions open?',
    })
    expect((options.headers as Record<string, string>).Authorization).toBeUndefined()
  })

  it('rejects malformed successful responses instead of exposing unknown fields', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      answer: 'Unsafe shape', status: 'success', sources: [], provider: 'private',
    }), { status: 200, headers: { 'content-type': 'application/json' } }))

    // Extra response fields are removed by the public allow-list projection.
    await expect(publicChat({ institution_code: 'GIT', message: 'Hello' })).resolves.toEqual({
      answer: 'Unsafe shape', status: 'success', sources: [],
    })

    vi.mocked(fetch).mockResolvedValueOnce(new Response('{bad json', { status: 200 }))
    await expect(publicChat({ institution_code: 'GIT', message: 'Hello' })).rejects.toMatchObject({
      kind: 'malformed_response',
    })
  })

  it('maps non-JSON API failures without returning backend details', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('provider stack trace', { status: 502 }))
    await expect(publicChat({ institution_code: 'GIT', message: 'Hello' })).rejects.toEqual(
      expect.objectContaining<Partial<PublicChatError>>({ kind: 'server', status: 502 }),
    )
  })

  it.each([429, 503])('maps overload status %s to a safe busy error without retrying', async (status) => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      error: { code: 'INTERNAL_DETAIL', message: 'provider and quota details' },
    }), { status, headers: { 'content-type': 'application/json', 'retry-after': '2' } }))

    await expect(publicChat({ institution_code: 'GIT', message: 'Hello' })).rejects.toEqual(
      expect.objectContaining<Partial<PublicChatError>>({ kind: 'busy', status }),
    )
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('distinguishes caller cancellation from a timeout', async () => {
    vi.mocked(fetch).mockImplementationOnce((_input, init) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => {
        reject(new DOMException('cancelled detail', 'AbortError'))
      })
    }))
    const controller = new AbortController()
    const request = publicChat(
      { institution_code: 'GIT', message: 'Hello' },
      { timeoutMs: 10_000, signal: controller.signal },
    )
    controller.abort()
    await expect(request).rejects.toMatchObject({ kind: 'aborted' })
  })
})

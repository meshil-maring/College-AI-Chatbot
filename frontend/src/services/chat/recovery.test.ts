import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, chat } from './api.ts'
import { ChatDeadlineError, withDeadline } from './deadline.ts'
import { getChatTurn } from './recovery.ts'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('bounded chat transport', () => {
  it('aborts an unconfirmed request without automatically repeating the POST', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn(
      (_url: string, options: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          options.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        }),
    )
    vi.stubGlobal('fetch', fetcher)
    const result = chat({ user_query: 'Question', institution_id: 'college', turn_id: 'turn' }, 'token')
    const assertion = expect(result).rejects.toBeInstanceOf(ChatDeadlineError)
    await vi.advanceTimersByTimeAsync(90_000)
    await assertion
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('removes its deadline after a successful operation', async () => {
    vi.useFakeTimers()
    expect(await withDeadline(100, async () => 'complete')).toBe('complete')
    expect(vi.getTimerCount()).toBe(0)
  })

  it('uses a read-only owner-authenticated status endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ state: 'processing' }), { status: 200 }))
    vi.stubGlobal('fetch', fetcher)
    expect(await getChatTurn('turn/with path', 'current-token')).toEqual({ state: 'processing' })
    const [url, options] = fetcher.mock.calls[0]
    expect(url).toBe('/api/v1/generation/turns/turn%2Fwith%20path')
    expect(options.headers).toEqual({ Authorization: 'Bearer current-token' })
    expect(options.body).toBeUndefined()
  })

  it('keeps the safe server error code available to the recovery UI', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: 'CHAT_TURN_NOT_FOUND', message: 'Chat turn not found.' },
          }),
          { status: 404 },
        ),
      ),
    )
    await expect(getChatTurn('missing', 'token')).rejects.toBeInstanceOf(ApiError)
  })
})

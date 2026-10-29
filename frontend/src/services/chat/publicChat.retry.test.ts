import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { publicChat } from './publicChat.ts'

const question = { institution_code: 'GIT', message: 'Library opening hours?' }
const reply = { answer: 'The library opens at nine.', status: 'success', sources: [] }

beforeEach(() => vi.stubGlobal('fetch', vi.fn()))
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

function stalledFetch(bodyOnly = false) {
  let signal: AbortSignal | null | undefined
  const wait = () =>
    new Promise<Response>((_resolve, reject) => {
      signal?.addEventListener('abort', () => reject(new DOMException('Private detail', 'AbortError')))
    })
  vi.mocked(fetch).mockImplementationOnce((_url, options) => {
    signal = options?.signal
    return bodyOnly ? Promise.resolve({ ok: true, status: 200, json: wait } as unknown as Response) : wait()
  })
  return () => signal
}

describe('public chat full-response deadline', () => {
  it.each([false, true])('times out once while waiting for %s (false=headers, true=body)', async (bodyOnly) => {
    vi.useFakeTimers()
    const signal = stalledFetch(bodyOnly)
    const result = publicChat(question, 100)
    const assertion = expect(result).rejects.toMatchObject({ kind: 'timeout' })
    await vi.advanceTimersByTimeAsync(100)
    await assertion
    expect(signal()?.aborted).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('handles caller cancellation during response-body loading and cleans the deadline', async () => {
    vi.useFakeTimers()
    const signal = stalledFetch(true)
    const caller = new AbortController()
    const result = publicChat(question, { timeoutMs: 1000, signal: caller.signal })
    const assertion = expect(result).rejects.toMatchObject({ kind: 'aborted' })
    await Promise.resolve()
    caller.abort()
    await assertion
    expect(signal()?.aborted).toBe(true)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('does not POST an already cancelled request', async () => {
    const caller = new AbortController()
    caller.abort()
    await expect(publicChat(question, { signal: caller.signal })).rejects.toMatchObject({ kind: 'aborted' })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('cleans the deadline after success and omits browser credentials', async () => {
    vi.useFakeTimers()
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(reply), { status: 200 }))
    await expect(publicChat(question)).resolves.toEqual(reply)
    expect(vi.mocked(fetch).mock.calls[0][1]?.credentials).toBe('omit')
    expect(vi.getTimerCount()).toBe(0)
  })

  it.each([
    ['3', 3],
    ['0', 0],
    ['999999', 3600],
    ['garbage', null],
    ['-1', null],
    ['1.5', null],
  ])('reads a safe Retry-After delay from %s', async (header, expected) => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response('Private provider detail', {
        status: 429,
        headers: { 'Retry-After': header },
      }),
    )
    await expect(publicChat(question)).rejects.toMatchObject({ kind: 'busy', status: 429, retryAfterSeconds: expected })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('accepts an HTTP-date retry delay without exposing server error contents', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-29T00:00:00Z'))
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response('Private provider detail', {
        status: 503,
        headers: { 'Retry-After': 'Thu, 29 Oct 2026 00:00:05 GMT' },
      }),
    )
    await expect(publicChat(question)).rejects.toMatchObject({ kind: 'busy', retryAfterSeconds: 5 })
    expect(vi.getTimerCount()).toBe(0)
  })
})

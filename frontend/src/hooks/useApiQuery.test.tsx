import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useApiQuery } from './useApiQuery.ts'
import { clearNavigationQueryCache, NAVIGATION_QUERY_POLICY, queryClient } from '../lib/queryClient.ts'

const key = ['admin', 'academic-setup', 'session-token']
const cache = { cache: 'navigation' } as const

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

describe('navigation query caching', () => {
  it('reuses fresh data on remount without another request', async () => {
    const read = vi.fn().mockResolvedValue('saved catalogue')
    const first = renderHook(() => useApiQuery(key, read, true, cache))
    await waitFor(() => expect(first.result.current.data).toBe('saved catalogue'))
    first.unmount()
    const second = renderHook(() => useApiQuery(key, read, true, cache))
    expect(second.result.current.data).toBe('saved catalogue')
    expect(second.result.current.isPending).toBe(false)
    expect(second.result.current.isFetching).toBe(false)
    expect(read).toHaveBeenCalledTimes(1)
  })

  it('deduplicates concurrent reads using the same session key', async () => {
    let resolve!: (data: string) => void
    const read = vi.fn(() => new Promise<string>((done) => { resolve = done }))
    const first = renderHook(() => useApiQuery(key, read, true, cache))
    const second = renderHook(() => useApiQuery(key, read, true, cache))
    expect(read).toHaveBeenCalledTimes(1)
    await act(async () => resolve('shared catalogue'))
    await waitFor(() => expect(first.result.current.data).toBe('shared catalogue'))
    expect(second.result.current.data).toBe('shared catalogue')
  })

  it('keeps stale data visible while refreshing after the freshness window', async () => {
    let resolve!: (data: string) => void
    const read = vi.fn().mockResolvedValueOnce('cached catalogue').mockImplementationOnce(() => new Promise<string>((done) => { resolve = done }))
    const first = renderHook(() => useApiQuery(key, read, true, cache))
    await waitFor(() => expect(first.result.current.data).toBe('cached catalogue'))
    first.unmount()
    const realNow = Date.now
    vi.spyOn(Date, 'now').mockImplementation(() => realNow() + NAVIGATION_QUERY_POLICY.staleTime + 1)
    const second = renderHook(() => useApiQuery(key, read, true, cache))
    expect(second.result.current.data).toBe('cached catalogue')
    expect(second.result.current.isPending).toBe(false)
    expect(second.result.current.isFetching).toBe(true)
    expect(read).toHaveBeenCalledTimes(2)
    await act(async () => resolve('updated catalogue'))
    await waitFor(() => expect(second.result.current.data).toBe('updated catalogue'))
  })

  it('refetches an invalidated inactive query even when its data is recent', async () => {
    const read = vi.fn().mockResolvedValueOnce('old options').mockResolvedValueOnce('new options')
    const first = renderHook(() => useApiQuery(key, read, true, cache))
    await waitFor(() => expect(first.result.current.data).toBe('old options'))
    first.unmount()
    await queryClient.invalidateQueries({ queryKey: key })
    expect(read).toHaveBeenCalledTimes(1)
    const second = renderHook(() => useApiQuery(key, read, true, cache))
    await waitFor(() => expect(second.result.current.data).toBe('new options'))
    expect(read).toHaveBeenCalledTimes(2)
  })

  it('does not expose the previous session data when the token changes', async () => {
    let resolve!: (data: string) => void
    const read = vi.fn().mockResolvedValueOnce('old session records').mockImplementationOnce(() => new Promise<string>((done) => { resolve = done }))
    const view = renderHook(({ token }) => useApiQuery(['admin', 'academic-setup', token], read, true, cache), { initialProps: { token: 'old' } })
    await waitFor(() => expect(view.result.current.data).toBe('old session records'))
    view.rerender({ token: 'new' })
    expect(view.result.current.data).toBeUndefined()
    await act(async () => resolve('new session records'))
    await waitFor(() => expect(view.result.current.data).toBe('new session records'))
  })

  it('discards a pending result when the session cache is cleared', async () => {
    let resolve!: (data: string) => void
    const read = vi.fn(() => new Promise<string>((done) => { resolve = done }))
    const view = renderHook(() => useApiQuery(key, read, true, cache))
    view.unmount()
    clearNavigationQueryCache()
    await act(async () => resolve('retired session records'))
    expect(queryClient.getQueryData(key)).toBeUndefined()
  })

  it('removes unused data after the retention window', async () => {
    vi.useFakeTimers()
    const read = vi.fn().mockResolvedValue('catalogue')
    const view = renderHook(() => useApiQuery(key, read, true, cache))
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(queryClient.getQueryData(key)).toBe('catalogue')
    view.unmount()
    await act(async () => { await vi.advanceTimersByTimeAsync(NAVIGATION_QUERY_POLICY.gcTime + 1) })
    expect(queryClient.getQueryData(key)).toBeUndefined()
  })

  it('preserves the existing mount-specific behavior for queries without caching', async () => {
    const read = vi.fn().mockResolvedValue('data')
    const first = renderHook(() => useApiQuery(key, read))
    await waitFor(() => expect(first.result.current.data).toBe('data'))
    first.unmount()
    const second = renderHook(() => useApiQuery(key, read))
    await waitFor(() => expect(second.result.current.data).toBe('data'))
    expect(read).toHaveBeenCalledTimes(2)
  })
})

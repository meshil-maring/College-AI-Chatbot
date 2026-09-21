/**
 * Phase 6.16 — Student API client tests.
 *
 * Covers the read-only contract surface only: correct tenant-scoped URLs, the
 * Bearer header, 401 session-expiry notification, typed errors, and the
 * absence of any mutation function on this client.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  StudentApiError,
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from './studentApi.ts'
import * as studentApi from './studentApi.ts'
import { onSessionExpired } from './sessionEvents.ts'

describe('studentApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('getMyAcademicProfile sends GET to the academic-profile endpoint with Bearer auth', async () => {
    const mockFetch = vi.mocked(fetch)
    const profile = { register_number: 'REG-1', email: 's@t.edu' }
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(profile), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    const result = await getMyAcademicProfile('token-1')
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/students/me/academic-profile')
    expect((options.headers as Record<string, string>).Authorization).toBe('Bearer token-1')
    expect(result.register_number).toBe('REG-1')
  })

  it('getMyAttendanceSummary sends GET to the attendance summary endpoint', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ summary: {}, records: [] }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    await getMyAttendanceSummary('t')
    const [url] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/students/me/attendance/summary')
  })

  it('getMyResultsSummary and getMyTestResultsSummary hit their own endpoints', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ summary: {}, records: [] }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ summary: {}, records: [] }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    await getMyResultsSummary('t')
    await getMyTestResultsSummary('t')
    const urls = mockFetch.mock.calls.map((call) => (call as [string, RequestInit])[0])
    expect(urls).toEqual(['/api/v1/students/me/results/summary', '/api/v1/students/me/test-results/summary'])
  })

  it('getMyNotices and getMyResources send a limit query value', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], total: 0 }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], total: 0 }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    await getMyNotices('t', 5)
    await getMyResources('t', 6)
    const urls = mockFetch.mock.calls.map((call) => (call as [string, RequestInit])[0])
    expect(urls[0]).toContain('/api/v1/students/me/notices?limit=5')
    expect(urls[1]).toContain('/api/v1/students/me/resources?limit=6')
  })

  it('a 401 notifies session expiry with the token used and raises a typed error', async () => {
    const mockFetch = vi.mocked(fetch)
    const seen: (string | null)[] = []
    const unsubscribe = onSessionExpired((token) => { seen.push(token) })
    try {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'expired' }), { status: 401, headers: { 'content-type': 'application/json' } }),
      )
      await expect(getMyAttendanceSummary('stale-token')).rejects.toBeInstanceOf(StudentApiError)
      expect(seen).toEqual(['stale-token'])
    } finally {
      unsubscribe()
    }
  })

  it('a 403 keeps the typed code without a session-expiry notification', async () => {
    const mockFetch = vi.mocked(fetch)
    const seen: (string | null)[] = []
    const unsubscribe = onSessionExpired((token) => { seen.push(token) })
    try {
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ error: { code: 'FORBIDDEN', message: 'No' } }), { status: 403, headers: { 'content-type': 'application/json' } }),
      )
      await expect(getMyNotices('t')).rejects.toMatchObject({ status: 403, code: 'FORBIDDEN' })
      expect(seen).toEqual([])
    } finally {
      unsubscribe()
    }
  })

  it('a network failure raises NETWORK_ERROR', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockRejectedValueOnce(new Error('down'))
    await expect(getMyResources('t')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 })
  })

  it('exposes no mutation functions (read-only client)', () => {
    const names = Object.keys(studentApi).filter((name) => name !== 'StudentApiError')
    expect(names.sort()).toEqual([
      'getMyAcademicProfile',
      'getMyAttendanceSummary',
      'getMyNotices',
      'getMyResources',
      'getMyResultsSummary',
      'getMyTestResultsSummary',
    ])
  })
})

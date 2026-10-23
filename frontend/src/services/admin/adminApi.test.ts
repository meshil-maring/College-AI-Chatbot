/**
 * Phase Admin-4 — Admin API client tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminApiError, createFaq, getAdminIdentity, listFaqs, listPendingStudents, listAuditLogs } from './adminApi.ts'

describe('adminApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('filters student history on the server while preserving existing audit requests', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockImplementation(
      async () => new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    await listAuditLogs('token', 100, 'student_registrations')
    expect(mockFetch.mock.calls[0][0]).toBe('/api/v1/admin/audit-logs?limit=100&table_name=student_registrations')
    await listAuditLogs('token')
    expect(mockFetch.mock.calls[1][0]).toBe('/api/v1/admin/audit-logs?limit=50')
  })

  it('getAdminIdentity sends GET to /api/v1/admin/me with auth header', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ user_id: 'u1', is_admin: true, roles: ['admin'] }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    const result = await getAdminIdentity('test-token')
    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/admin/me')
    expect(options.method).toBe('GET')
    expect(options.headers).toEqual({ Authorization: 'Bearer test-token' })
    expect(result.is_admin).toBe(true)
  })

  it('listFaqs sends GET with auth header', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    const result = await listFaqs('token')
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/admin/faqs')
    expect(options.headers).toEqual({ Authorization: 'Bearer token' })
    expect(result).toEqual([])
  })

  it('createFaq sends POST with JSON body', async () => {
    const mockFetch = vi.mocked(fetch)
    const faq = { faq_id: 'f1', question: 'Q?', answer: 'A.', is_active: true }
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(faq), { status: 201, headers: { 'content-type': 'application/json' } }),
    )
    const result = await createFaq('token', { question: 'Q?', answer: 'A.' })
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/admin/faqs')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body as string)).toEqual({ question: 'Q?', answer: 'A.' })
    expect(result.faq_id).toBe('f1')
  })

  it('lists pending account decisions without a client-supplied institution', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    await listPendingStudents('token')
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/v1/admin/students/pending?limit=100&offset=0')
  })

  it('throws AdminApiError with status on 403 forbidden', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Not admin' } }), {
        status: 403,
        headers: { 'content-type': 'application/json' },
      }),
    )
    await expect(getAdminIdentity('token')).rejects.toMatchObject({ status: 403, code: 'FORBIDDEN' })
  })

  it('throws AdminApiError with status on 500 server error', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Server error' }), {
        status: 500,
        headers: { 'content-type': 'application/json' },
      }),
    )
    await expect(getAdminIdentity('token')).rejects.toMatchObject({ status: 500 })
  })

  it('throws AdminApiError with NETWORK_ERROR when fetch rejects', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockRejectedValueOnce(new Error('Network down'))
    await expect(getAdminIdentity('token')).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })
})

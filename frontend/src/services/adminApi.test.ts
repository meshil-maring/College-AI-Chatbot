/**
 * Phase Admin-4 — Admin API client tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AdminApiError,
  createFaq,
  getAdminIdentity,
  getDashboardSummary,
  getMyProfile,
  listFaqs,
  listStudents,
  uploadResultsCsv,
} from './adminApi.ts'

describe('adminApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
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

  it('getDashboardSummary returns the typed institution-scoped payload', async () => {
    const mockFetch = vi.mocked(fetch)
    const body = {
      institution: { name: 'Alpha University', code: 'ALPHA', status: 'active' },
      students: { total: 10, pending_approvals: 1, approved: 9, active: 8 },
      knowledge: {
        sources_total: 4,
        sources_active: 3,
        documents_total: 5,
        failed_processing_runs: null,
      },
      communication: { active_faqs: 5, active_notices: 2, recent_notices: [] },
      academics: { attendance_records: 7, test_results: 3, results: 4 },
      quick_actions: [],
    }
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    const result = await getDashboardSummary('token')
    expect(result.institution.code).toBe('ALPHA')
    expect(result.students.total).toBe(10)
    expect(result.communication.active_faqs).toBe(5)
    expect(result.knowledge.failed_processing_runs).toBeNull()
  })

  it('getDashboardSummary never sends a client-supplied institution_id', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )
    await getDashboardSummary('token')
    const url = String(mockFetch.mock.calls[0][0])
    expect(url).not.toContain('institution_id')
    expect(url.endsWith('/v1/admin/dashboard')).toBe(true)
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

  it('listStudents sends GET with institution_id query param', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    await listStudents('token', 'inst-123')
    const [url] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/admin/students')
    expect(url).toContain('institution_id=inst-123')
  })

  it('getMyProfile sends GET to /api/v1/students/me/profile', async () => {
    const mockFetch = vi.mocked(fetch)
    const profile = { student_id: 's1', student_number: 'S100', status: 'active' }
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(profile), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    const result = await getMyProfile('token')
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/students/me/profile')
    expect(options.method).toBe('GET')
    expect(result.student_number).toBe('S100')
  })

  it('uploadResultsCsv sends POST with FormData', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ uploaded: 10 }), { status: 200, headers: { 'content-type': 'application/json' } }),
    )
    const file = new File(['csv,data'], 'results.csv', { type: 'text/csv' })
    const result = await uploadResultsCsv('token', file)
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/admin/results/csv-upload')
    expect(options.method).toBe('POST')
    expect(options.body).toBeInstanceOf(FormData)
    expect(result).toEqual({ uploaded: 10 })
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
    await expect(getDashboardSummary('token')).rejects.toMatchObject({ status: 500 })
  })

  it('throws AdminApiError with NETWORK_ERROR when fetch rejects', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockRejectedValueOnce(new Error('Network down'))
    await expect(getAdminIdentity('token')).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { adminStudentWorkspaceApi as api } from './adminStudentWorkspaceApi.ts'

afterEach(() => vi.unstubAllGlobals())

describe('Admin Students API routing', () => {
  it('sends saved cohort filters and archived cohort reads through Admin routes', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response('[]', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.getRegistrations('token', 'section-1', 0, 25, 'ACTIVE', { batchId: 'batch-1', search: 'Ada & Ben', sort: 'student_name' })
    const url = new URL(fetchMock.mock.calls[0][0], 'http://localhost')
    expect(url.pathname).toBe('/api/v1/admin/student-workspace/sections/section-1/registrations')
    expect(Object.fromEntries(url.searchParams)).toEqual({ limit: '25', offset: '0', registration: 'ACTIVE', batch_id: 'batch-1', search: 'Ada & Ben', sort: 'student_name' })
    await api.getBatches('token', 'section-1', true)
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/admin/student-workspace/sections/section-1/batches?include_inactive=true')
  })

  it('uses only Admin endpoints for roster, profile, history, batch selection and saving', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    await api.getSections('token')
    await api.getStudents('token', 'section-1', new URLSearchParams({ search: 'Ada' }))
    await api.getProfile('token', 'roster-1', 50)
    await api.getHistory('token', 'section-1', new URLSearchParams({ offset: '25' }))
    await api.getBatches('token', 'section-1')
    await api.getRegistrations('token', 'section-1', 100, 100, 'PENDING_APPROVAL')
    const input = { student_name: 'Ada Rao', register_number: 'CS001', batch_id: 'batch-1' }
    await api.createRegistration('token', 'section-1', input)
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/admin/student-workspace/sections',
      '/api/v1/admin/student-workspace/sections/section-1/students?search=Ada',
      '/api/v1/admin/student-workspace/roster/roster-1/profile?offset=50',
      '/api/v1/admin/student-workspace/sections/section-1/history?offset=25',
      '/api/v1/admin/student-workspace/sections/section-1/batches',
      '/api/v1/admin/student-workspace/sections/section-1/registrations?limit=100&offset=100&registration=PENDING_APPROVAL',
      '/api/v1/admin/student-workspace/sections/section-1/registrations',
    ])
    expect(fetchMock.mock.calls[6][1]).toMatchObject({ method: 'POST', body: JSON.stringify(input), headers: { Authorization: 'Bearer token' } })
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createClassStudentRegistration, getClassStudentRegistrations, getRegistrationBatches, sendStudentRegistrationInvitation } from './studentRegistrationApi.ts'
import { onSessionExpired } from './sessionEvents.ts'

const fetchMock = vi.fn()
beforeEach(() => vi.stubGlobal('fetch', fetchMock.mockReset()))
afterEach(() => vi.unstubAllGlobals())

describe('class registration API', () => {
  it('requests email only for a saved registration and never sends a client recipient', async () => {
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }))
    await sendStudentRegistrationInvitation('token', 'section', 'registration')
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/faculty/student-registrations/sections/section/registration/invitation', expect.objectContaining({ method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer token' }) }))
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined()
  })
  it('loads configured batches through the authenticated class scope', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }))
    expect(await getRegistrationBatches('test-token', 'scope-section')).toEqual([])
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/faculty/student-registrations/sections/scope-section/batches')
  })
  it('sends the cohort and identity while using the section only as an authorization reference', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ registration_id: 'r1' }), { status: 201 }))
    const data = { student_name: 'Ada Rao', register_number: '001', batch_id: 'batch-1', email: 'ada@college.edu' }
    await createClassStudentRegistration('test-token', 'scope-section', data)
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/faculty/student-registrations/sections/scope-section', expect.objectContaining({ method: 'POST', headers: { Authorization: 'Bearer test-token', 'Content-Type': 'application/json' }, body: JSON.stringify(data) }))
    expect(fetchMock.mock.calls[0][1].body).not.toContain('course_id')
  })

  it('passes pagination and approval status to the server', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }))
    await getClassStudentRegistrations('test-token', 'scope-section', 25, 25, 'PENDING_APPROVAL')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/faculty/student-registrations/sections/scope-section?limit=25&offset=25&registration=PENDING_APPROVAL')
  })

  it('sends cohort and search filters together and includes archived cohorts only when requested', async () => {
    fetchMock.mockImplementation(async () => new Response('[]', { status: 200 }))
    await getClassStudentRegistrations('test-token', 'scope-section', 0, 25, 'ACTIVE', { batchId: 'batch-1', search: 'Ada & Ben', sort: 'student_name' })
    const url = new URL(fetchMock.mock.calls[0][0], 'http://localhost')
    expect(Object.fromEntries(url.searchParams)).toEqual({ limit: '25', offset: '0', registration: 'ACTIVE', batch_id: 'batch-1', search: 'Ada & Ben', sort: 'student_name' })
    await getRegistrationBatches('test-token', 'scope-section', true)
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/faculty/student-registrations/sections/scope-section/batches?include_inactive=true')
  })

  it('reuses session expiration and exposes safe migration or permission errors', async () => {
    const expired = vi.fn(), unsubscribe = onSessionExpired(expired)
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ error: { message: 'Session expired', code: 'UNAUTHORIZED' } }), { status: 401 }))
    try {
      await expect(getClassStudentRegistrations('test-token', 'scope')).rejects.toMatchObject({ status: 401, message: 'Session expired' })
      expect(expired).toHaveBeenCalledWith('test-token')
    } finally { unsubscribe() }
  })
})

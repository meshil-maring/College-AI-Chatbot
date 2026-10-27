import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createStructureRecord, getAcademicStructure, updateStructureRecord } from './academicStructure.ts'
import { ADMIN_BASE } from './http.ts'

const fetchMock = vi.fn()
beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ institution_id: 'institution-1', records: {}, manageable: [], activities: [] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
})
describe('Academic structure transport', () => {
  it('reads through the authenticated backend', async () => {
    await getAcademicStructure('token')
    expect(fetchMock).toHaveBeenCalledWith(
      `${ADMIN_BASE}/academic-structure`,
      expect.objectContaining({ method: 'GET', headers: { Authorization: 'Bearer token' } }),
    )
  })
  it('posts typed records and safely encodes update identifiers', async () => {
    await createStructureRecord('token', 'program_semesters', {
      program_id: 'program',
      name: 'Semester 1',
      code: 'S1',
      semester_number: 1,
      is_active: true,
    })
    expect(fetchMock).toHaveBeenLastCalledWith(
      `${ADMIN_BASE}/academic-structure/program_semesters`,
      expect.objectContaining({ method: 'POST' }),
    )
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }))
    await updateStructureRecord('token', 'academic_sections', 'id/with space', { capacity: null })
    expect(fetchMock).toHaveBeenLastCalledWith(
      `${ADMIN_BASE}/academic-structure/academic_sections/id%2Fwith%20space`,
      expect.objectContaining({ method: 'PATCH', body: '{"capacity":null}' }),
    )
  })
})

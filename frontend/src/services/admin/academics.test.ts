import { afterEach, describe, expect, it, vi } from 'vitest'
import { createAcademicRecord, getAcademicSetup, updateAcademicRecord } from './academics.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Academic Setup API transport', () => {
  it('reads the catalogue and sends degree programs to their distinct endpoint', async () => {
    const catalogue = {
      institution_id: 'institution-1',
      records: {
        departments: [
          {
            department_id: 'department-1',
            institution_id: 'institution-1',
            name: 'CSE',
            code: 'CSE',
            description: null,
            is_active: true,
          },
        ],
      },
      manageable: ['departments'],
    }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(catalogue), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    expect(await getAcademicSetup('opaque-token')).toEqual(catalogue)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/admin/academic-setup',
      expect.objectContaining({
        method: 'GET',
        headers: { Authorization: 'Bearer opaque-token' },
      }),
    )
    const payload = {
      name: 'B.Tech CSE',
      code: 'BTECH-CSE',
      description: null,
      department_id: 'department-1',
      degree_type: 'B.Tech',
      duration_years: 4,
      total_credits: null,
      is_active: true,
    }
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }))
    await createAcademicRecord('opaque-token', 'programs', payload)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/admin/academic-setup/programs',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    )
  })

  it('encodes record identifiers and propagates server validation messages', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Active programs still use this department.' }), {
        status: 422,
        headers: { 'content-type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await expect(updateAcademicRecord('token', 'departments', 'department/a', { is_active: false })).rejects.toThrow(
      'Active programs still use this department.',
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/admin/academic-setup/departments/department%2Fa',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('sends dated semesters and teaching course hours to distinct endpoints', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response('{}', { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const semester = {
      name: 'Fifth Semester',
      code: 'CSE-2026-S5',
      is_active: true,
      academic_year_id: 'year-1',
      semester_number: 1,
      start_date: '2026-07-01',
      end_date: '2026-12-31',
      is_current: false,
    }
    await createAcademicRecord('token', 'semesters', semester)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/admin/academic-setup/semesters',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(semester) }),
    )
    const subject = {
      name: 'Data Mining',
      code: 'CSE-DM',
      description: null,
      is_active: true,
      department_id: 'department-1',
      credits: 3.5,
      lecture_hours: 3,
      tutorial_hours: null,
      practical_hours: 2,
    }
    await createAcademicRecord('token', 'courses', subject)
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/admin/academic-setup/courses',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(subject) }),
    )
    await updateAcademicRecord('token', 'semesters', 'semester-5', { name: 'Fifth Semester updated' })
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/admin/academic-setup/semesters/semester-5',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: 'Fifth Semester updated' }) }),
    )
    await updateAcademicRecord('token', 'courses', 'course-1', { credits: 4, is_active: false })
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/admin/academic-setup/courses/course-1',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ credits: 4, is_active: false }) }),
    )
  })

  it.each([
    ['courses', 409, 'Subject code already exists.'],
    ['semesters', 404, 'Parent not found.'],
    ['courses', 403, 'Missing scoped permission.'],
  ] as const)('propagates %s %s validation and authorization failures', async (entity, status, detail) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail }), {
          status,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    )
    await expect(updateAcademicRecord('token', entity, 'record-1', { is_active: false })).rejects.toThrow(detail)
  })
})

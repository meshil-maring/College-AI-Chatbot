import { describe, expect, it, vi } from 'vitest'
import type { Course } from '../../../../../types/academicSetup.ts'
import type { CurriculumSubject, ProgramSemester } from '../../../../../types/academicStructure.ts'
import { parseSubjectCsv, SUBJECT_TEMPLATE, validateSubjectRows } from '../import/subjectImportModel.ts'
import { runSubjectImport, type ImportApi, type RowResult } from '../import/runSubjectImport.ts'

const existing = [{ course_id: 'c-old', code: 'MA101', department_id: 'd1' } as Course]
const csv = [
  'Code,Name,Credits,L,T,P,Semester,Type,Required',
  'CS101,Programming,4,3,1,2,1,core,',
  'ma101,Mathematics I,4,3,1,0,1,,yes',
  'CS205,Machine Learning,3,3,0,0,5,elective,',
  'CS101,Duplicate,abc,,,,9,lab,maybe',
].join('\n')

describe('subject CSV parsing and validation', () => {
  it('reads the downloadable template', () => {
    expect(validateSubjectRows(parseSubjectCsv(SUBJECT_TEMPLATE), [], 8).every((row) => !row.errors.length)).toBe(true)
  })

  it('rejects files without the required columns or rows', () => {
    expect(() => parseSubjectCsv('title_only\nx')).toThrow('"code" and "name"')
    expect(() => parseSubjectCsv('code,name\n')).toThrow('no subject rows')
  })

  it('applies defaults, reuses existing codes and reports every problem on a row', () => {
    const [cs101, ma101, ml, broken] = validateSubjectRows(parseSubjectCsv(csv), existing, 8)
    expect(cs101).toMatchObject({ sourceRow: 2, credits: 4, semester: 1, course_type: 'core', is_required: true })
    expect(ma101).toMatchObject({ existingCourseId: 'c-old', errors: [] })
    expect(ml).toMatchObject({ course_type: 'elective', is_required: false, semester: 5 })
    expect(broken.errors).toEqual([
      'Code is repeated (also on row 2).',
      'Type must be core, elective, open elective, skill or project.',
      'Required must be yes or no.',
      'Semester must be a whole number from 1 to 8.',
      'Credits must be greater than zero.',
    ])
  })

  it('ignores the semester column when no curriculum is chosen', () => {
    const rows = validateSubjectRows(parseSubjectCsv('code,name,semester\nX1,Subject,42'), [], null)
    expect(rows[0]).toMatchObject({ semester: null, errors: [] })
  })
})

describe('subject import run', () => {
  function api(fail = new Set<string>()): ImportApi {
    return {
      createCourse: vi.fn(async (payload) => {
        if (fail.has(payload.code)) throw new Error('Server rejected')
        return { ...payload, course_id: `c-${payload.code}`, institution_id: 'i' } as Course
      }),
      createStage: vi.fn(
        async (payload) => ({ ...payload, program_semester_id: `s-${payload.semester_number}` }) as ProgramSemester,
      ),
      createMapping: vi.fn(async (payload) => ({ ...payload, curriculum_subject_id: 'm' }) as CurriculumSubject),
    }
  }
  const rows = validateSubjectRows(parseSubjectCsv(csv), existing, 8)
  const target = {
    departmentId: 'd1',
    curriculum: { curriculum_version_id: 'v1', program_id: 'p1' },
    stages: [{ program_semester_id: 's-1', semester_number: 1 } as ProgramSemester],
    mappings: [] as CurriculumSubject[],
  }

  it('creates new subjects, reuses existing ones, adds missing semesters once and skips invalid rows', async () => {
    const calls = api()
    const results = await runSubjectImport(rows, target, calls, new Map(), vi.fn())
    expect(calls.createCourse).toHaveBeenCalledTimes(2)
    expect(calls.createStage).toHaveBeenCalledTimes(1)
    expect(calls.createStage).toHaveBeenCalledWith(expect.objectContaining({ semester_number: 5, code: 'SEM-5' }))
    expect(calls.createMapping).toHaveBeenCalledTimes(3)
    expect(calls.createMapping).toHaveBeenCalledWith(
      expect.objectContaining({ course_id: 'c-old', program_semester_id: 's-1', is_required: true }),
    )
    expect([...results.keys()]).toEqual([2, 3, 4])
  })

  it('does not place a subject that the curriculum already has', async () => {
    const calls = api()
    const mapped = { ...target, mappings: [{ course_id: 'c-old' } as CurriculumSubject] }
    await runSubjectImport(rows, mapped, calls, new Map(), vi.fn())
    expect(calls.createMapping).not.toHaveBeenCalledWith(expect.objectContaining({ course_id: 'c-old' }))
  })

  it('keeps going after a failure and a retry repeats only the failed row', async () => {
    const first = api(new Set(['CS205']))
    const progress = vi.fn()
    const results = await runSubjectImport(rows, target, first, new Map(), progress)
    expect(results.get(4)).toEqual({ status: 'failed', courseId: undefined, message: 'Server rejected' })
    expect(results.get(2)?.status).toBe('done')
    expect(progress).toHaveBeenCalledTimes(3)
    const second = api()
    const retried = await runSubjectImport(rows, target, second, results as Map<number, RowResult>, vi.fn())
    expect(second.createCourse).toHaveBeenCalledTimes(1)
    expect(second.createCourse).toHaveBeenCalledWith(expect.objectContaining({ code: 'CS205' }))
    expect(retried.get(4)?.status).toBe('done')
  })
})

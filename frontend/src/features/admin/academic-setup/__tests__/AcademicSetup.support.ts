import { beforeEach, vi } from 'vitest'
import * as api from '../../../../services/admin/academics.ts'
import type { AcademicCatalogue, AcademicYear, DegreeProgram, Department } from '../../../../types/academicSetup.ts'
import { academicRecordId } from '../academicSetupForm.ts'

const auth = vi.hoisted(() => ({
  accessToken: 'token-1' as string | null,
  role: 'admin',
  status: 'authenticated',
  user: { user_id: 'admin-1', institution_id: 'institution-1', effective_permissions: ['*'] },
}))
vi.mock('../../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../../services/admin/academics.ts')

export const department: Department = {
  department_id: 'department-1',
  institution_id: 'institution-1',
  name: 'Computer Science and Engineering',
  code: 'CSE',
  description: null,
  is_active: true,
}
export const program: DegreeProgram = {
  program_id: 'program-1',
  institution_id: 'institution-1',
  department_id: department.department_id,
  name: 'B.Tech CSE',
  code: 'BTECH-CSE',
  description: null,
  degree_type: 'B.Tech',
  duration_years: 4,
  total_credits: 160,
  is_active: true,
}
export const year: AcademicYear = {
  academic_year_id: 'year-1',
  institution_id: 'institution-1',
  name: '2026–2027',
  code: '2026-27',
  start_date: '2026-07-01',
  end_date: '2027-06-30',
  is_current: true,
  is_active: true,
}
export let catalogue: AcademicCatalogue
export function setCatalogue(value: AcademicCatalogue) {
  catalogue = value
}

beforeEach(() => {
  vi.resetAllMocks()
  auth.accessToken = 'token-1'
  auth.role = 'admin'
  auth.status = 'authenticated'
  auth.user.user_id = 'admin-1'
  auth.user.institution_id = 'institution-1'
  auth.user.effective_permissions = ['*']
  catalogue = {
    institution_id: 'institution-1',
    records: { departments: [structuredClone(department)], programs: [], academic_years: [] },
    manageable: ['departments', 'programs', 'academic_years'],
  }
  vi.mocked(api.getAcademicSetup).mockImplementation(async () => structuredClone(catalogue))
  vi.mocked(api.createAcademicRecord).mockImplementation(async (_token, entity, payload) => {
    const primaryKey = {
      departments: 'department_id',
      programs: 'program_id',
      academic_years: 'academic_year_id',
      semesters: 'semester_id',
      courses: 'course_id',
      program_courses: 'program_course_id',
      course_offerings: 'course_offering_id',
      sections: 'section_id',
    }[entity]
    const record = { [primaryKey]: `new-${entity}`, institution_id: catalogue.institution_id, ...payload }
    catalogue.records[entity]?.push(record as never)
    return record as never
  })
  vi.mocked(api.updateAcademicRecord).mockImplementation(async (_token, entity, id, payload) => {
    const records = catalogue.records[entity] ?? []
    const record = records.find((item) => academicRecordId(item) === id)
    if (!record) throw new Error('Record not found')
    Object.assign(record, payload)
    return structuredClone(record) as never
  })
})

export { auth }

import { beforeEach, vi } from 'vitest'
import * as api from '../../../../services/admin/academics.ts'
import * as structureApi from '../../../../services/admin/academicStructure.ts'
import * as registrationApi from '../../../../services/academics/semesterRegistration.ts'
import type { RegistrationCatalogue } from '../../../../types/semesterRegistration.ts'
import type { StructureCatalogue, StructureEntity, StructureRecordMap } from '../../../../types/academicStructure.ts'
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
vi.mock('../../../../services/admin/academicStructure.ts')
vi.mock('../../../../services/academics/semesterRegistration.ts')

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
export let structureCatalogue: StructureCatalogue
export let registrationCatalogue: RegistrationCatalogue
export function setStructureCatalogue(value: StructureCatalogue) {
  structureCatalogue = value
}
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
  registrationCatalogue = {
    institution_id: 'institution-1',
    groups: [],
    students: [],
    assignments: [],
    can_manage_choices: true,
    can_assign: true,
  }
  vi.mocked(registrationApi.getRegistrationCatalogue).mockImplementation(async () =>
    structuredClone(registrationCatalogue),
  )
  vi.mocked(registrationApi.saveChoiceGroup).mockImplementation(async (_token, draft, id) => {
    const groupId = id ?? `group-${registrationCatalogue.groups.length + 1}`
    const group = {
      ...structuredClone(draft),
      choice_group_id: groupId,
      institution_id: registrationCatalogue.institution_id,
      options: draft.options.map((option, index) => ({
        ...structuredClone(option),
        choice_option_id: `${groupId}-option-${index + 1}`,
      })),
    }
    registrationCatalogue.groups = [
      ...registrationCatalogue.groups.filter((item) => item.choice_group_id !== groupId),
      group,
    ]
    return { choice_group_id: groupId, institution_id: registrationCatalogue.institution_id }
  })
  vi.mocked(registrationApi.deleteChoiceGroup).mockImplementation(async (_token, id) => {
    registrationCatalogue.groups = registrationCatalogue.groups.filter((group) => group.choice_group_id !== id)
    return { choice_group_id: id, institution_id: registrationCatalogue.institution_id }
  })
  catalogue = {
    institution_id: 'institution-1',
    records: { departments: [structuredClone(department)], programs: [], academic_years: [] },
    manageable: ['departments', 'programs', 'academic_years'],
  }
  vi.mocked(api.getAcademicSetup).mockImplementation(async () => structuredClone(catalogue))
  structureCatalogue = {
    institution_id: 'institution-1',
    records: {
      program_semesters: [],
      curriculum_versions: [],
      curriculum_subjects: [],
      admission_cohorts: [],
      academic_sections: [],
      academic_offerings: [],
    },
    manageable: [
      'program_semesters',
      'curriculum_versions',
      'curriculum_subjects',
      'admission_cohorts',
      'academic_sections',
      'academic_offerings',
    ],
    activities: [],
  }
  vi.mocked(structureApi.getAcademicStructure).mockImplementation(async () => structuredClone(structureCatalogue))
  vi.mocked(structureApi.createStructureRecord).mockImplementation(async (_token, entity, payload) => {
    const key = `${entity.slice(0, -1)}_id`
    let id = `new-${entity}`
    for (
      let suffix = 2;
      structureCatalogue.records[entity]?.some((item) => (item as unknown as Record<string, unknown>)[key] === id);
      suffix += 1
    )
      id = `new-${entity}-${suffix}`
    const record = {
      ...payload,
      [key]: id,
      institution_id: structureCatalogue.institution_id,
      created_at: '2026-10-27T00:00:00Z',
      updated_at: '2026-10-27T00:00:00Z',
      ...(entity === 'curriculum_versions' ? { status: 'draft', published_at: null } : {}),
      ...(entity === 'admission_cohorts' ? { is_active: true } : {}),
    }
    structureCatalogue.records[entity]?.push(record as never)
    return record as never
  })
  vi.mocked(structureApi.updateStructureRecord).mockImplementation(
    async (_token, entity: StructureEntity, id, payload) => {
      const row = (structureCatalogue.records[entity] as StructureRecordMap[StructureEntity][] | undefined)?.find(
        (item) => (item as unknown as Record<string, unknown>)[`${entity.slice(0, -1)}_id`] === id,
      )
      if (!row) throw new Error('Record not found')
      Object.assign(row, payload)
      return structuredClone(row) as never
    },
  )
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

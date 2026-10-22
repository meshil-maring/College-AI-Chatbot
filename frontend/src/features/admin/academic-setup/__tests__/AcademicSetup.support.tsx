import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import * as api from '../../../../services/admin/adminApi.ts'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import * as packagesApi from '../../../../services/academics/academicPackagesApi.ts'
import { catalogue } from '../../../academic-packages/__tests__/fixtures.ts'
import { useAcademicSetup } from '../useAcademicSetup.ts'
import AcademicRecordForm from '../ui/AcademicRecordForm.tsx'
import AcademicRecordTable from '../ui/AcademicRecordTable.tsx'
import { useAcademicDirectory } from '../useAcademicDirectory.ts'
vi.mock('../../../../services/admin/adminApi.ts')
vi.mock('../../../../services/academics/academicPackagesApi.ts')

export const fixture = (): AcademicCatalogue => ({
  institution_id: 'tenant',
  manageable: [
    'departments',
    'programs',
    'academic_years',
    'semesters',
    'courses',
    'program_courses',
    'course_offerings',
    'sections',
    'batches',
  ],
  records: {
    batches: [],
    departments: [
      { department_id: 'd', name: 'Science', code: 'SCI', is_active: true },
      { department_id: 'inactive', name: 'Archived', code: 'OLD', is_active: false },
    ],
    programs: [
      { program_id: 'p', department_id: 'd', name: 'Science degree', code: 'BS', is_active: true },
      { program_id: 'blocked', department_id: 'inactive', name: 'Unavailable', code: 'BAD', is_active: true },
    ],
    academic_years: [
      {
        academic_year_id: 'y',
        name: '2026-27',
        code: 'Y26',
        start_date: '2026-07-01',
        end_date: '2027-06-30',
        is_active: true,
      },
    ],
    semesters: [
      { semester_id: 's', academic_year_id: 'y', name: 'Semester 1', code: 'S1', is_active: true },
      { semester_id: 'other', academic_year_id: 'other-year', name: 'Foreign term', code: 'OTHER', is_active: true },
    ],
    courses: [
      { course_id: 'c', department_id: 'd', name: 'Mathematics', code: 'MATH', is_active: true },
      { course_id: 'not-linked', department_id: 'd', name: 'Physics', code: 'PHY', is_active: true },
    ],
    program_courses: [
      {
        program_course_id: 'pc',
        program_id: 'p',
        course_id: 'c',
        semester_id: null,
        course_type: 'core',
        is_required: true,
        is_active: true,
      },
    ],
    course_offerings: [
      {
        course_offering_id: 'o',
        program_id: 'p',
        course_id: 'c',
        academic_year_id: 'y',
        semester_id: 's',
        is_active: true,
      },
    ],
    sections: [],
  },
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getAcademicCatalogue).mockResolvedValue(fixture())
  vi.mocked(api.saveAcademicRecord).mockResolvedValue({ saved: true })
  vi.mocked(packagesApi.getAcademicPackages).mockResolvedValue(catalogue())
  vi.mocked(packagesApi.commandAcademicPackage).mockResolvedValue({})
})

export async function loaded() {
  await screen.findByRole('button', { name: /^Add / }, { timeout: 5000 })
}

export function tab(name: string) {
  const entities: Record<string, string> = {
    Departments: 'departments',
    Programs: 'programs',
    Batches: 'batches',
    'Academic Years': 'academic_years',
    Semesters: 'semesters',
    'Courses / Subjects': 'courses',
    'Course Offerings': 'course_offerings',
    'Program Curriculum': 'program_courses',
  }
  const entity = entities[name]
  const harness = screen.queryByLabelText('Test record type')
  if (harness) return fireEvent.change(harness, { target: { value: entity } })
  const stage = ['departments', 'programs', 'batches'].includes(entity)
    ? 'College basics'
    : ['academic_years', 'semesters'].includes(entity)
      ? 'Calendar'
      : 'Subjects'
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`^[1-6] ${stage}$`) }))
  const selector = screen.queryByLabelText('Record type')
  if (selector) fireEvent.change(selector, { target: { value: entity } })
}

// Retains transport/form compatibility checks for legacy entities outside the admin setup journey.
export function AcademicRecordHarness({ accessToken }: { accessToken: string }) {
  const state = useAcademicSetup(accessToken)
  const directory = useAcademicDirectory(state.data, state.entity)
  return (
    <>
      <select
        aria-label="Test record type"
        value={state.entity}
        onChange={(event) => state.reset(event.target.value as typeof state.entity)}
      >
        {state.available.map((entity) => (
          <option key={entity} value={entity}>
            {entity}
          </option>
        ))}
      </select>
      {state.data && (
        <>
          <AcademicRecordTable state={state} directory={directory} />
          {state.formOpen && <AcademicRecordForm state={state} />}
          {state.notice && <p>{state.notice}</p>}
          {state.error && <p role="alert">{state.error}</p>}
        </>
      )}
    </>
  )
}

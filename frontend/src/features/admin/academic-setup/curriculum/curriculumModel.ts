import type {
  AcademicCatalogue,
  AcademicRecord,
  Course,
  DegreeProgram,
  ProgramCourse,
  Semester,
} from '../../../../types/academicSetup.ts'

export const CURRICULUM_PAGE_SIZE = 7
export type CurriculumTab = 'list' | 'structure' | 'mapping' | 'history'
export type DetailTab = 'overview' | 'structure' | 'subjects' | 'outcomes'
export type CurriculumStatus = 'all' | 'active' | 'inactive'
export type CurriculumSort = 'name-asc' | 'name-desc' | 'code-asc'

export function scopedCurriculumCatalogue(catalogue: AcademicCatalogue | undefined, institutionId: string) {
  if (!catalogue || catalogue.institution_id !== institutionId) return undefined
  return {
    ...catalogue,
    records: Object.fromEntries(
      Object.entries(catalogue.records).map(([entity, rows]) => [
        entity,
        (rows as AcademicRecord[]).filter((row) => row.institution_id === institutionId),
      ]),
    ) as AcademicCatalogue['records'],
  }
}

export function filterCurriculumPrograms(
  programs: DegreeProgram[],
  search: string,
  programId: string,
  status: CurriculumStatus,
  sort: CurriculumSort,
) {
  const needle = search.trim().toLocaleLowerCase()
  const field = sort.startsWith('code') ? 'code' : 'name'
  return programs
    .filter((program) => `${program.name} ${program.code}`.toLocaleLowerCase().includes(needle))
    .filter((program) => !programId || program.program_id === programId)
    .filter((program) => status === 'all' || program.is_active === (status === 'active'))
    .sort(
      (left, right) =>
        (left[field].localeCompare(right[field], undefined, { numeric: true, sensitivity: 'base' }) ||
          left.program_id.localeCompare(right.program_id)) * (sort.endsWith('desc') ? -1 : 1),
    )
}

export function mappingCredits(links: ProgramCourse[], courses: Course[] | undefined) {
  const values = links.map((link) => courses?.find((course) => course.course_id === link.course_id)?.credits)
  if (values.some((value) => value == null)) return undefined
  return values.reduce<number>((total, value) => total + (value ?? 0), 0)
}

export function semesterGroups(links: ProgramCourse[], semesters: Semester[] | undefined) {
  const ids = [...new Set(links.map((link) => link.semester_id))]
  return ids
    .map((id) => {
      const semester = semesters?.find((item) => item.semester_id === id)
      return {
        id: id ?? 'unassigned',
        semester,
        label: id ? (semester ? `Semester ${semester.semester_number}` : 'Semester unavailable') : 'All semesters',
        links: links.filter((link) => link.semester_id === id),
      }
    })
    .sort(
      (left, right) =>
        (left.semester?.semester_number ?? Infinity) - (right.semester?.semester_number ?? Infinity) ||
        left.id.localeCompare(right.id),
    )
}

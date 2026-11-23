import type { AcademicCatalogue, Course } from '../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'

export const SUBJECT_PAGE_SIZE = 10
export type SubjectSortField = 'code' | 'name' | 'is_active'
export type SubjectSort = `${SubjectSortField}-${'asc' | 'desc'}`
export type SubjectStatus = 'all' | 'active' | 'inactive'

export function subjectDepartments(catalogue: AcademicCatalogue | undefined, institutionId: string) {
  return catalogue?.records.departments?.filter((item) => item.institution_id === institutionId)
}

// A reusable subject can have different types/semesters in different curricula.
// Keep each assignment together so combined filters match the same relationship.
export function subjectAssignments(
  _catalogue: AcademicCatalogue | undefined,
  institutionId: string,
  structure?: StructureCatalogue,
) {
  const scoped = structure?.institution_id === institutionId ? structure.records : undefined
  const stages = scoped?.program_semesters?.filter((item) => item.institution_id === institutionId)
  const mappings = scoped?.curriculum_subjects?.filter((item) => item.institution_id === institutionId)
  return {
    semesters: stages?.map((item) => ({
      semester_id: item.program_semester_id,
      semester_number: item.semester_number,
      name: `Program: ${item.name}`,
      code: item.code,
    })),
    links: mappings?.map((item) => ({
      course_id: item.course_id,
      semester_id: item.program_semester_id,
      course_type: item.course_type,
    })),
  }
}

export function filterSubjects(
  records: Course[],
  assignments: ReturnType<typeof subjectAssignments>,
  filters: {
    search: string
    department: string
    semester: string
    type: string
    status: SubjectStatus
    sort: SubjectSort
  },
) {
  const needle = filters.search.trim().toLocaleLowerCase()
  const [field, direction] = filters.sort.split('-') as [SubjectSortField, 'asc' | 'desc']
  return records
    .filter((record) => `${record.name} ${record.code}`.toLocaleLowerCase().includes(needle))
    .filter((record) => !filters.department || record.department_id === filters.department)
    .filter((record) => filters.status === 'all' || record.is_active === (filters.status === 'active'))
    .filter(
      (record) =>
        (!filters.semester && !filters.type) ||
        assignments.links?.some(
          (link) =>
            link.course_id === record.course_id &&
            (!filters.semester || link.semester_id === filters.semester) &&
            (!filters.type || link.course_type === filters.type),
        ),
    )
    .sort((left, right) => {
      const order = String(left[field]).localeCompare(String(right[field]), undefined, {
        numeric: true,
        sensitivity: 'base',
      })
      return (order || left.course_id.localeCompare(right.course_id)) * (direction === 'asc' ? 1 : -1)
    })
}

export function assignmentLabels(courseId: string, assignments: ReturnType<typeof subjectAssignments>) {
  const links = assignments.links?.filter((item) => item.course_id === courseId)
  const types = links ? [...new Set(links.map((item) => item.course_type))] : undefined
  const semesterIds = [...new Set(links?.flatMap((item) => (item.semester_id ? [item.semester_id] : [])) ?? [])]
  const semesters =
    !links || !assignments.semesters
      ? 'Unavailable'
      : !semesterIds.length
        ? 'Unassigned'
        : semesterIds
            .map((id) => assignments.semesters?.find((item) => item.semester_id === id))
            .map((item) => (item ? String(item.semester_number) : 'Unavailable'))
            .join(', ')
  return { types, semesters }
}

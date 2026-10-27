import type { AcademicCatalogue, DegreeProgram, Department } from '../../../../types/academicSetup.ts'

export const PROGRAM_PAGE_SIZE = 8
export const DEGREE_TYPES = ['B.Tech', 'M.Tech', 'B.Sc', 'M.Sc', 'B.A', 'M.A', 'B.Com', 'M.Com', 'Diploma', 'Other']
export type ProgramSortField =
  'name' | 'code' | 'department' | 'degree_type' | 'duration_years' | 'total_credits' | 'is_active'
export type ProgramSort = `${ProgramSortField}-${'asc' | 'desc'}`
export type ProgramStatus = 'all' | 'active' | 'inactive'
export interface ProgramDraft {
  name: string
  code: string
  department_id: string
  degree_type: string
  duration_years: string
  total_credits: string
  description: string
  is_active: boolean
}
export type ProgramErrors = Partial<Record<keyof ProgramDraft, string>>

export function programDraft(record?: DegreeProgram): ProgramDraft {
  return {
    name: record?.name ?? '',
    code: record?.code ?? '',
    department_id: record?.department_id ?? '',
    degree_type: record?.degree_type ?? '',
    duration_years: record ? String(record.duration_years) : '',
    total_credits: record?.total_credits == null ? '' : String(record.total_credits),
    description: record?.description ?? '',
    is_active: record?.is_active ?? true,
  }
}

export function programDepartments(catalogue: AcademicCatalogue | undefined, institutionId: string) {
  return catalogue?.records.departments?.filter((department) => department.institution_id === institutionId)
}

// Match the existing API limits; degree types and fractional durations remain supported.
export function validateProgram(draft: ProgramDraft, departments: Department[], editing: boolean): ProgramErrors {
  const errors: ProgramErrors = {}
  if (!draft.name.trim()) errors.name = 'Enter a program name.'
  else if (draft.name.trim().length > 160) errors.name = 'Use 160 characters or fewer.'
  if (!draft.code.trim()) errors.code = 'Enter a program code.'
  else if (draft.code.trim().length > 32) errors.code = 'Use 32 characters or fewer.'
  if (!draft.department_id) errors.department_id = 'Select a department.'
  else if (!editing && !departments.some((item) => item.department_id === draft.department_id && item.is_active))
    errors.department_id = 'Select an available active department.'
  if (!draft.degree_type.trim()) errors.degree_type = 'Select a degree type.'
  else if (draft.degree_type.trim().length > 160) errors.degree_type = 'Use 160 characters or fewer.'
  if (
    !draft.duration_years.trim() ||
    !Number.isFinite(Number(draft.duration_years)) ||
    Number(draft.duration_years) <= 0
  )
    errors.duration_years = 'Enter a duration greater than zero.'
  if (draft.total_credits.trim() && !Number.isFinite(Number(draft.total_credits)))
    errors.total_credits = 'Enter a valid number of credits.'
  if (draft.description.trim().length > 2000) errors.description = 'Use 2,000 characters or fewer.'
  return errors
}

export function filterPrograms(
  records: DegreeProgram[],
  departments: Department[],
  search: string,
  department: string,
  degree: string,
  status: ProgramStatus,
  sort: ProgramSort,
) {
  const needle = search.trim().toLocaleLowerCase()
  const [field, direction] = sort.split('-') as [ProgramSortField, 'asc' | 'desc']
  const departmentNames = new Map(departments.map((item) => [item.department_id, item.name]))
  function value(record: DegreeProgram) {
    return field === 'department' ? (departmentNames.get(record.department_id) ?? '') : record[field]
  }
  return records
    .filter((record) => `${record.name} ${record.code}`.toLocaleLowerCase().includes(needle))
    .filter((record) => !department || record.department_id === department)
    .filter((record) => !degree || record.degree_type === degree)
    .filter((record) => status === 'all' || record.is_active === (status === 'active'))
    .sort((a, b) => {
      const left = value(a)
      const right = value(b)
      // Keep missing optional credits at the end in both directions.
      if (left == null || right == null) return left == null ? (right == null ? 0 : 1) : -1
      const order =
        typeof left === 'number' && typeof right === 'number'
          ? left - right
          : String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: 'base' })
      return (order || a.program_id.localeCompare(b.program_id)) * (direction === 'asc' ? 1 : -1)
    })
}

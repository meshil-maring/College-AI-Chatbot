import type { AcademicCatalogue, Department } from '../../../../types/academicSetup.ts'

export type DepartmentSort = 'name-asc' | 'name-desc' | 'code-asc' | 'code-desc'
export type DepartmentStatus = 'all' | 'active' | 'inactive'
export interface DepartmentDraft {
  name: string
  code: string
  description: string
  is_active: boolean | null
}
export type DepartmentErrors = Partial<Record<keyof DepartmentDraft, string>>
export const DEPARTMENT_PAGE_SIZE = 5

export function departmentDraft(record?: Department): DepartmentDraft {
  return {
    name: record?.name ?? '',
    code: record?.code ?? '',
    description: record?.description ?? '',
    is_active: record?.is_active ?? null,
  }
}

// These limits mirror the existing DepartmentCreate API, not the proposed model.
export function validateDepartment(draft: DepartmentDraft): DepartmentErrors {
  const errors: DepartmentErrors = {}
  if (!draft.name.trim()) errors.name = 'Enter a department name.'
  else if (draft.name.trim().length > 160) errors.name = 'Use 160 characters or fewer.'
  if (!draft.code.trim()) errors.code = 'Enter a department code.'
  else if (draft.code.trim().length > 32) errors.code = 'Use 32 characters or fewer.'
  if (draft.description.trim().length > 2000) errors.description = 'Use 2,000 characters or fewer.'
  if (draft.is_active === null) errors.is_active = 'Choose a department status.'
  return errors
}

export function departmentPrograms(catalogue: AcademicCatalogue | undefined, departmentId: string) {
  return catalogue?.records.programs?.filter(
    (program) => program.institution_id === catalogue.institution_id && program.department_id === departmentId,
  )
}

export function filterDepartments(
  records: Department[],
  search: string,
  status: DepartmentStatus,
  sort: DepartmentSort,
) {
  const needle = search.trim().toLocaleLowerCase()
  const [field, direction] = sort.split('-') as ['name' | 'code', 'asc' | 'desc']
  return records
    .filter((record) => `${record.name} ${record.code}`.toLocaleLowerCase().includes(needle))
    .filter((record) => status === 'all' || record.is_active === (status === 'active'))
    .sort((a, b) => {
      const order = a[field].localeCompare(b[field], undefined, { numeric: true, sensitivity: 'base' })
      return (order || a.department_id.localeCompare(b.department_id)) * (direction === 'asc' ? 1 : -1)
    })
}

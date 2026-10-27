import { useState } from 'react'
import { AdminApiError } from '../../../../services/admin/http.ts'
import { useAcademicStructure } from '../structure/useAcademicStructure.ts'
import {
  filterSubjects,
  subjectAssignments,
  subjectDepartments,
  SUBJECT_PAGE_SIZE,
  type SubjectSort,
  type SubjectStatus,
} from './subjectModel.ts'

export interface SubjectsContext {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
}
export function useSubjects(context: SubjectsContext) {
  const { query, catalogue, loading, error, structure, busy } = useAcademicStructure(context)
  const denied = query.error instanceof AdminApiError && [401, 403].includes(query.error.status)
  const availableCatalogue = denied ? undefined : catalogue
  const records = availableCatalogue?.records.courses?.filter((item) => item.institution_id === context.institutionId)
  const departments = subjectDepartments(availableCatalogue, context.institutionId)
  const assignments = subjectAssignments(availableCatalogue, context.institutionId, structure)
  const [search, changeSearch] = useState('')
  const [department, changeDepartment] = useState('')
  const [semester, changeSemester] = useState('')
  const [type, changeType] = useState('')
  const [status, changeStatus] = useState<SubjectStatus>('all')
  const [sort, changeSort] = useState<SubjectSort>('code-asc')
  const [requestedPage, setPage] = useState(1)
  const filtered = filterSubjects(records ?? [], assignments, { search, department, semester, type, status, sort })
  const pages = Math.max(1, Math.ceil(filtered.length / SUBJECT_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  const manageable = Boolean(records && availableCatalogue?.manageable.includes('courses'))
  const canCreate = manageable && Boolean(departments?.some((item) => item.is_active))
  function resetPage<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
    }
  }
  function clearFilters() {
    changeSearch('')
    changeDepartment('')
    changeSemester('')
    changeType('')
    changeStatus('all')
    setPage(1)
  }
  return {
    query,
    catalogue: availableCatalogue,
    records,
    departments,
    assignments,
    loading,
    error,
    denied: denied || Boolean(availableCatalogue && !records),
    manageable,
    canCreate,
    busy,
    search,
    department,
    semester,
    type,
    status,
    sort,
    page,
    pages,
    filtered,
    rows: filtered.slice((page - 1) * SUBJECT_PAGE_SIZE, page * SUBJECT_PAGE_SIZE),
    setSearch: resetPage(changeSearch),
    setDepartment: resetPage(changeDepartment),
    setSemester: resetPage(changeSemester),
    setType: resetPage(changeType),
    setStatus: resetPage(changeStatus),
    setSort: resetPage(changeSort),
    setPage,
    clearFilters,
  }
}
export type SubjectsState = ReturnType<typeof useSubjects>

import { useState } from 'react'
import { AdminApiError } from '../../../../services/admin/http.ts'
import { useAcademicOverview } from '../overview/useAcademicOverview.ts'
import {
  filterPrograms,
  programDepartments,
  PROGRAM_PAGE_SIZE,
  type ProgramSort,
  type ProgramStatus,
} from './programModel.ts'

export interface ProgramsContext {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
}

export function usePrograms(context: ProgramsContext) {
  const { query, catalogue, loading, error } = useAcademicOverview(
    context.accessToken,
    context.identity,
    context.institutionId,
    context.canReadCatalogues,
  )
  const denied = query.error instanceof AdminApiError && [401, 403].includes(query.error.status)
  const availableCatalogue = denied ? undefined : catalogue
  const records = availableCatalogue?.records.programs?.filter((item) => item.institution_id === context.institutionId)
  const departments = programDepartments(availableCatalogue, context.institutionId)
  const [search, changeSearch] = useState('')
  const [department, changeDepartment] = useState('')
  const [degree, changeDegree] = useState('')
  const [status, changeStatus] = useState<ProgramStatus>('all')
  const [sort, changeSort] = useState<ProgramSort>('name-asc')
  const [requestedPage, setPage] = useState(1)
  const filtered = filterPrograms(records ?? [], departments ?? [], search, department, degree, status, sort)
  const pages = Math.max(1, Math.ceil(filtered.length / PROGRAM_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  const manageable = Boolean(records && availableCatalogue?.manageable.includes('programs'))
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
    changeDegree('')
    changeStatus('all')
    setPage(1)
  }
  return {
    query,
    catalogue: availableCatalogue,
    records,
    departments,
    loading,
    error,
    denied: denied || Boolean(availableCatalogue && !records),
    manageable,
    canCreate,
    busy: query.isFetching || Boolean(error),
    search,
    department,
    degree,
    status,
    sort,
    page,
    pages,
    filtered,
    rows: filtered.slice((page - 1) * PROGRAM_PAGE_SIZE, page * PROGRAM_PAGE_SIZE),
    degreeTypes: [...new Set((records ?? []).map((item) => item.degree_type))].sort(),
    setSearch: resetPage(changeSearch),
    setDepartment: resetPage(changeDepartment),
    setDegree: resetPage(changeDegree),
    setStatus: resetPage(changeStatus),
    setSort: resetPage(changeSort),
    setPage,
    clearFilters,
  }
}
export type ProgramsState = ReturnType<typeof usePrograms>

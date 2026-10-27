import { useState } from 'react'
import { AdminApiError } from '../../../../services/admin/http.ts'
import { useAcademicOverview } from '../overview/useAcademicOverview.ts'
import {
  DEPARTMENT_PAGE_SIZE,
  filterDepartments,
  type DepartmentSort,
  type DepartmentStatus,
} from './departmentModel.ts'

export interface DepartmentsContext {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
}

export function useDepartments(context: DepartmentsContext) {
  const { query, catalogue, loading, error } = useAcademicOverview(
    context.accessToken,
    context.identity,
    context.institutionId,
    context.canReadCatalogues,
  )
  const denied = query.error instanceof AdminApiError && [401, 403].includes(query.error.status)
  const availableCatalogue = denied ? undefined : catalogue
  const records = availableCatalogue?.records.departments?.filter(
    (record) => record.institution_id === context.institutionId,
  )
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<DepartmentStatus>('all')
  const [sort, setSort] = useState<DepartmentSort>('name-asc')
  const [requestedPage, setPage] = useState(1)
  const filtered = filterDepartments(records ?? [], search, status, sort)
  const pages = Math.max(1, Math.ceil(filtered.length / DEPARTMENT_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  const manageable = Boolean(records && availableCatalogue?.manageable.includes('departments'))

  function changeSearch(value: string) {
    setSearch(value)
    setPage(1)
  }
  function changeStatus(value: DepartmentStatus) {
    setStatus(value)
    setPage(1)
  }
  function changeSort(value: DepartmentSort) {
    setSort(value)
    setPage(1)
  }
  function clearFilters() {
    changeSearch('')
    changeStatus('all')
  }
  return {
    query,
    catalogue: availableCatalogue,
    records,
    loading,
    error,
    denied: denied || Boolean(availableCatalogue && !records),
    manageable,
    busy: query.isFetching || Boolean(error),
    search,
    status,
    sort,
    page,
    pages,
    filtered,
    rows: filtered.slice((page - 1) * DEPARTMENT_PAGE_SIZE, page * DEPARTMENT_PAGE_SIZE),
    setSearch: changeSearch,
    setStatus: changeStatus,
    setSort: changeSort,
    setPage,
    clearFilters,
  }
}

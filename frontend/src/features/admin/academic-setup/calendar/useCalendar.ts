import { useState } from 'react'
import { AdminApiError } from '../../../../services/admin/http.ts'
import { useAcademicOverview } from '../overview/useAcademicOverview.ts'
import {
  CALENDAR_PAGE_SIZE,
  filterPeriods,
  type CalendarSort,
  type CalendarStatus,
  type CalendarTab,
} from './calendarModel.ts'

export interface CalendarContext {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
}

export function useCalendar(context: CalendarContext, initialTab: CalendarTab) {
  const { query, catalogue, loading, error } = useAcademicOverview(
    context.accessToken,
    context.identity,
    context.institutionId,
    context.canReadCatalogues,
  )
  const denied = query.error instanceof AdminApiError && [401, 403].includes(query.error.status)
  const available = denied ? undefined : catalogue
  const years = available?.records.academic_years?.filter((item) => item.institution_id === context.institutionId)
  const semesters = available?.records.semesters?.filter((item) => item.institution_id === context.institutionId)
  const [tab, changeTab] = useState(initialTab)
  const [search, changeSearch] = useState('')
  const [status, changeStatus] = useState<CalendarStatus>('all')
  const [sort, changeSort] = useState<CalendarSort>('newest')
  const [requestedPage, setPage] = useState(1)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const filteredYears = filterPeriods(years ?? [], search, status, sort)
  const filteredSemesters = filterPeriods(semesters ?? [], search, status, sort)
  const count = tab === 'semesters' ? filteredSemesters.length : filteredYears.length
  const pages = Math.max(1, Math.ceil(count / CALENDAR_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  const offset = (page - 1) * CALENDAR_PAGE_SIZE
  function resetting<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
    }
  }
  return {
    query,
    catalogue: available,
    years,
    semesters,
    loading,
    error,
    tab,
    search,
    status,
    sort,
    page,
    pages,
    count,
    busy: query.isFetching || Boolean(error),
    canManageYears: Boolean(years && available?.manageable.includes('academic_years')),
    canManageSemesters: Boolean(semesters && available?.manageable.includes('semesters')),
    filteredYears,
    filteredSemesters,
    yearRows: filteredYears.slice(offset, offset + CALENDAR_PAGE_SIZE),
    semesterRows: filteredSemesters.slice(offset, offset + CALENDAR_PAGE_SIZE),
    setTab: resetting(changeTab),
    setSearch: resetting(changeSearch),
    setStatus: resetting(changeStatus),
    setSort: resetting(changeSort),
    setPage,
    isExpanded: (id: string) => expanded[id] ?? years?.some((year) => year.academic_year_id === id && year.is_current),
    toggle: (id: string, current: boolean) => setExpanded((value) => ({ ...value, [id]: !current })),
    clearFilters: () => {
      changeSearch('')
      changeStatus('all')
      setPage(1)
    },
  }
}
export type CalendarState = ReturnType<typeof useCalendar>

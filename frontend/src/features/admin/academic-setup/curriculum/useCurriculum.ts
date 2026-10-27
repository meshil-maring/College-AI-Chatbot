import { useState } from 'react'
import { AdminApiError } from '../../../../services/admin/http.ts'
import { useAcademicOverview } from '../overview/useAcademicOverview.ts'
import { academicParents } from '../academicSetupParents.ts'
import {
  CURRICULUM_PAGE_SIZE,
  filterCurriculumPrograms,
  scopedCurriculumCatalogue,
  type CurriculumSort,
  type CurriculumStatus,
  type CurriculumTab,
  type DetailTab,
} from './curriculumModel.ts'

export interface CurriculumContext {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
}
export function useCurriculum(context: CurriculumContext, initialTab: CurriculumTab) {
  const source = useAcademicOverview(
    context.accessToken,
    context.identity,
    context.institutionId,
    context.canReadCatalogues,
  )
  const denied = source.query.error instanceof AdminApiError && [401, 403].includes(source.query.error.status)
  const catalogue = denied ? undefined : scopedCurriculumCatalogue(source.catalogue, context.institutionId)
  const programs = catalogue?.records.programs
  const links = catalogue?.records.program_courses
  const [tab, setTab] = useState(initialTab)
  const [detailTab, setDetailTab] = useState<DetailTab>('structure')
  const [search, changeSearch] = useState('')
  const [programId, changeProgram] = useState('')
  const [status, changeStatus] = useState<CurriculumStatus>('all')
  const [sort, changeSort] = useState<CurriculumSort>('name-asc')
  const [requestedPage, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState('')
  const filtered = filterCurriculumPrograms(programs ?? [], search, programId, status, sort)
  const pages = Math.max(1, Math.ceil(filtered.length / CURRICULUM_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  const rows = filtered.slice((page - 1) * CURRICULUM_PAGE_SIZE, page * CURRICULUM_PAGE_SIZE)
  const selected = rows.find((item) => item.program_id === selectedId) ?? rows[0]
  const selectedLinks = selected ? links?.filter((link) => link.program_id === selected.program_id) : undefined
  const parents = catalogue ? academicParents(catalogue, 'program_courses') : undefined
  const busy = source.query.isFetching || Boolean(source.error)
  const manageable = Boolean(links && catalogue?.manageable.includes('program_courses'))
  const canAdd = Boolean(
    !busy && manageable && selected && parents?.programs.has(selected.program_id) && parents.courses.size,
  )
  function resetPage<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
      setSelectedId('')
    }
  }
  function clearFilters() {
    changeSearch('')
    changeProgram('')
    changeStatus('all')
    setPage(1)
    setSelectedId('')
  }
  return {
    ...source,
    catalogue,
    programs,
    links,
    parents,
    denied,
    busy,
    manageable,
    canAdd,
    courses: catalogue?.records.courses,
    semesters: catalogue?.records.semesters,
    search,
    programId,
    status,
    sort,
    tab,
    detailTab,
    page,
    pages,
    rows,
    filtered,
    selected,
    selectedLinks,
    setTab,
    setDetailTab,
    setPage,
    setSelectedId,
    setSearch: resetPage(changeSearch),
    setProgram: resetPage(changeProgram),
    setStatus: resetPage(changeStatus),
    setSort: resetPage(changeSort),
    clearFilters,
  }
}
export type CurriculumState = ReturnType<typeof useCurriculum>

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { StudentDirectoryFilter } from '../../../../types/admin/students.ts'
import { STUDENT_DIRECTORY_PAGE_SIZE, studentDirectoryQueryOptions } from './studentDirectoryQueries.ts'

export function useStudentDirectory(accessToken: string, identity: string) {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<StudentDirectoryFilter>('all')
  const [programId, setProgramId] = useState('')
  const [page, setPage] = useState(1)
  const query = useQuery(studentDirectoryQueryOptions(accessToken, identity, { search, status, programId, page }))

  function filterStatus(value: StudentDirectoryFilter) {
    setStatus(value)
    setPage(1)
  }

  function filterProgram(value: string) {
    setProgramId(value)
    setPage(1)
  }

  function submitSearch() {
    setSearch(searchInput.trim())
    setPage(1)
  }

  function clearFilters() {
    setSearchInput('')
    setSearch('')
    setStatus('all')
    setProgramId('')
    setPage(1)
  }

  const total = query.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / STUDENT_DIRECTORY_PAGE_SIZE))
  const currentPage = Math.min(page, pages)

  return {
    query,
    searchInput,
    status,
    programId,
    page: currentPage,
    pages,
    setSearchInput,
    setStatus: filterStatus,
    setProgramId: filterProgram,
    submitSearch,
    clearFilters,
    setPage,
    hasFilters: Boolean(search || programId || status !== 'all'),
  }
}

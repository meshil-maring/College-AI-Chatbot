import { useEffect, useState } from 'react'
import type { AcademicCatalogue, AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'
import { ACADEMIC_DEFINITIONS } from './academicSetupDefinitions.ts'
import { find, label, records, usable } from './academicSetupModel.ts'

export function inAcademicYear(
  data: AcademicCatalogue,
  entity: AcademicEntity,
  row: AcademicRecord,
  year: string,
): boolean {
  if (!year) return true
  if (entity === 'academic_years') return row.academic_year_id === year
  if (entity === 'semesters' || entity === 'course_offerings') return row.academic_year_id === year
  if (entity === 'sections') {
    return find(data, 'course_offerings', row.course_offering_id)?.academic_year_id === year
  }
  if (entity === 'program_courses' && row.semester_id) {
    return find(data, 'semesters', row.semester_id)?.academic_year_id === year
  }
  return true
}

export function useAcademicDirectory(data: AcademicCatalogue | undefined, entity: AcademicEntity) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [year, setYear] = useState('')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState('')
  const idKey = ACADEMIC_DEFINITIONS[entity].id
  const filtered = data
    ? records(data, entity).filter((row) => {
        const active = usable(data, entity, row)
        return (
          inAcademicYear(data, entity, row, year) &&
          (status === 'all' || (status === 'active' ? active : !active)) &&
          label(data, entity, row).toLowerCase().includes(search.trim().toLowerCase())
        )
      })
    : []
  const pages = Math.max(1, Math.ceil(filtered.length / 6))
  const currentPage = Math.min(page, pages)
  const visible = filtered.slice((currentPage - 1) * 6, currentPage * 6)
  const selected = visible.find((row) => String(row[idKey]) === selectedId) ?? visible[0]
  useEffect(() => {
    setSearch('')
    setStatus('all')
    setPage(1)
    setSelectedId('')
  }, [entity])
  function resetFilters() {
    setSearch('')
    setStatus('all')
    setPage(1)
    setSelectedId('')
  }
  return {
    search,
    setSearch: (value: string) => {
      setSearch(value)
      setPage(1)
    },
    status,
    setStatus: (value: string) => {
      setStatus(value)
      setPage(1)
    },
    year,
    setYear: (value: string) => {
      setYear(value)
      resetFilters()
    },
    page: currentPage,
    setPage,
    pages,
    filtered,
    visible,
    selected,
    setSelectedId,
    resetFilters,
  }
}
export type AcademicDirectoryState = ReturnType<typeof useAcademicDirectory>

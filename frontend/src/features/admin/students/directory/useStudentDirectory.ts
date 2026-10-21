import { GraduationCap, UserCheck, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { Student } from '../../../../types/admin.ts'
import { downloadCsv } from '../studentImport.ts'
import type { StudentSection } from '../studentSections.ts'
export function useStudentDirectory({
  students,
  loading,
  refreshing,
  error,
  search,
  onSearch,
  onRefresh,
  onSection,
}: {
  students: Student[]
  loading: boolean
  refreshing: boolean
  error: string | null
  search: string
  onSearch: (search: string) => void
  onRefresh: () => void
  onSection: (section: StudentSection) => void
}) {
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState(false)
  const [draftSearch, setDraftSearch] = useState(search)
  useEffect(() => {
    setDraftSearch(search)
    setPage(1)
  }, [search])
  const filtered = students.filter(
    (student) =>
      (status === 'all' ||
        (status === 'archived' ? !student.is_active : student.is_active && student.status === status)) &&
      student.student_number.toLowerCase().includes(search.trim().toLowerCase()),
  )
  const pages = Math.max(1, Math.ceil(filtered.length / 10))
  const currentPage = Math.min(page, pages)
  const visible = filtered.slice((currentPage - 1) * 10, currentPage * 10)
  const stats = [
    {
      title: 'Total Students',
      value: students.length,
      Icon: Users,
      color: 'neutral',
      filter: 'all',
      description: 'Across your institution',
    },
    {
      title: 'Active Students',
      value: students.filter((student) => student.is_active && student.status === 'active').length,
      Icon: UserCheck,
      color: 'valid',
      filter: 'active',
      description: 'Currently enrolled',
    },
    {
      title: 'Graduated',
      value: students.filter((student) => student.is_active && student.status === 'graduated').length,
      Icon: GraduationCap,
      color: 'duplicate',
      filter: 'graduated',
      description: 'Completed their studies',
    },
    {
      title: 'Archived Students',
      value: students.filter((student) => !student.is_active).length,
      Icon: Users,
      color: 'invalid',
      filter: 'archived',
      description: 'Academic records retained',
    },
  ]
  const exportRows = () =>
    downloadCsv('students.csv', [
      ['student_number', 'status', 'enrollment_date', 'expected_graduation_date', 'is_active'],
      ...filtered.map((student) => [
        student.student_number,
        student.status,
        student.enrollment_date,
        student.expected_graduation_date,
        student.is_active,
      ]),
    ])
  return {
    students,
    loading,
    refreshing,
    error,
    onSearch,
    onRefresh,
    onSection,
    status,
    setStatus,
    page,
    setPage,
    filters,
    setFilters,
    draftSearch,
    setDraftSearch,
    filtered,
    pages,
    currentPage,
    visible,
    stats,
    exportRows,
  }
}

export type StudentDirectoryModel = ReturnType<typeof useStudentDirectory>

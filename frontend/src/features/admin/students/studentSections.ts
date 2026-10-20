export type StudentSection = 'all' | 'add' | 'import' | 'requests'
export const STUDENT_SECTIONS: readonly {
  key: StudentSection
  label: string
}[] = [
  { key: 'all', label: 'All Students' },
  { key: 'add', label: 'Add Student' },
  { key: 'import', label: 'Bulk Import' },
  { key: 'requests', label: 'Registration Requests' },
]

export type SectionStatus = 'active' | 'inactive'
export type SectionSort = 'reference' | `${'name' | 'code' | 'status'}-${'asc' | 'desc'}`
export interface SectionDraft {
  name: string
  code: string
  batchId: string
  programSemesterId: string
  semesterId: string
  capacity: string
  description: string
  status: SectionStatus
}
export interface SectionRecord extends SectionDraft {
  id: string
  studentCount: number | null
  color: string
}
export interface SectionBatch {
  id: string
  name: string
  programId: string
  academicYear: string
}
export const SECTION_PAGE_SIZE = 10
export const sectionStatuses: { value: SectionStatus; label: string; description: string }[] = [
  { value: 'active', label: 'Active', description: 'Section is active and can be used' },
  { value: 'inactive', label: 'Inactive', description: 'Temporarily disabled' },
]
export function emptySection(): SectionDraft {
  return {
    name: '',
    code: '',
    batchId: '',
    programSemesterId: '',
    semesterId: '',
    capacity: '',
    description: '',
    status: 'active',
  }
}
export function sectionDraft(record: SectionRecord): SectionDraft {
  const { id: _id, studentCount: _students, color: _color, ...draft } = record
  return draft
}
export function sectionLabel(record: SectionRecord, batches: SectionBatch[]) {
  return `${record.name}, ${batches.find((batch) => batch.id === record.batchId)?.name ?? 'Unavailable batch'}`
}
export function filterSections(
  records: SectionRecord[],
  batches: SectionBatch[],
  filters: { search: string; batch: string; program: string; year: string; status: string; sort: SectionSort },
) {
  const search = filters.search.trim().toLowerCase()
  return records
    .filter((record) => {
      const batch = batches.find((item) => item.id === record.batchId)
      return (
        (!search || `${record.name} ${record.code} ${batch?.name}`.toLowerCase().includes(search)) &&
        (!filters.batch || record.batchId === filters.batch) &&
        (!filters.program || batch?.programId === filters.program) &&
        (!filters.year || batch?.academicYear === filters.year) &&
        (!filters.status || record.status === filters.status)
      )
    })
    .sort((a, b) => {
      if (filters.sort === 'reference') return 0
      const [field, direction] = filters.sort.split('-') as ['name' | 'code' | 'status', 'asc' | 'desc']
      const difference = a[field].localeCompare(b[field], undefined, { numeric: true })
      return direction === 'asc' ? difference : -difference
    })
}
export function validateSection(draft: SectionDraft, records: SectionRecord[], batches: SectionBatch[], id?: string) {
  if (!draft.name.trim() || !draft.code.trim()) return 'Enter a section name and code.'
  if (draft.name.trim().length > 160 || draft.code.trim().length > 32 || draft.description.length > 2000)
    return 'Use up to 160 characters for the name, 32 for the code and 2000 for the description.'
  if (!id && !batches.some((item) => item.id === draft.batchId)) return 'Select a batch.'
  if (draft.capacity && (!/^\d+$/.test(draft.capacity) || !Number.isSafeInteger(Number(draft.capacity))))
    return 'Maximum capacity must be a nonnegative whole number.'
  const record = records.find((item) => item.id === id)
  if (draft.capacity && record?.studentCount != null && Number(draft.capacity) < record.studentCount)
    return 'Maximum capacity cannot be less than the current student count.'
  if (records.some((item) => item.id !== id && item.code.toLowerCase() === draft.code.trim().toLowerCase()))
    return 'A section with this code already exists.'
  return undefined
}

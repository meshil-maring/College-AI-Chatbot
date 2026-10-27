import { useState } from 'react'
import { BATCH_PAGE_SIZE, filterBatches, type BatchRecord, type BatchSort } from './batchModel.ts'
import { batchChoices, storedBatch } from './batchStorage.ts'
import { useAcademicStructure, type StructureContext } from '../structure/useAcademicStructure.ts'
import { useStructureWrite } from '../structure/useStructureWrite.ts'

export function useBatches(context: StructureContext) {
  const source = useAcademicStructure(context)
  const write = useStructureWrite(source, 'admission_cohorts')
  const records = (source.structure?.records.admission_cohorts ?? []).map(storedBatch)
  const choices = batchChoices(source)
  const [search, changeSearch] = useState('')
  const [program, changeProgram] = useState('')
  const [year, changeYear] = useState('')
  const [status, changeStatus] = useState('')
  const [sort, changeSort] = useState<BatchSort>('year-desc')
  const [requestedPage, setPage] = useState(1)
  const [notice, setNotice] = useState('')
  const filtered = filterBatches(records, choices.programs, { search, program, year, status, sort })
  const pages = Math.max(1, Math.ceil(filtered.length / BATCH_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  function filter<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
    }
  }
  function clearFilters() {
    changeSearch('')
    changeProgram('')
    changeYear('')
    changeStatus('')
    setPage(1)
  }
  async function save(record: BatchRecord, existing: boolean) {
    const payload = {
      name: record.name.trim(),
      code: record.code.trim(),
      description: record.description.trim() || null,
      expected_count: record.expectedCount ? Number(record.expectedCount) : null,
      status: record.status,
    }
    const saved = await write.save(
      existing ? record.id : undefined,
      existing
        ? payload
        : {
            ...payload,
            program_id: record.programId,
            curriculum_version_id: record.curriculumId,
            academic_year_id: record.academicYear,
            start_year: Number(record.startYear),
            end_year: Number(record.endYear),
          },
    )
    if (saved) {
      clearFilters()
      changeSort('year-desc')
      setNotice(`${record.name} ${existing ? 'updated' : 'created'} successfully.`)
    }
    return saved
  }
  const canManage = source.canManage('admission_cohorts')
  const canCreate =
    canManage &&
    choices.programs.some(
      (item) => item.active && choices.curricula.some((version) => version.active && version.programId === item.id),
    ) &&
    choices.years.some((item) => item.is_active)
  return {
    ...source,
    source,
    ...choices,
    write,
    records,
    search,
    program,
    year,
    status,
    sort,
    page,
    pages,
    filtered,
    notice,
    save,
    available: source.structure?.records.admission_cohorts !== undefined,
    canManage,
    canCreate,
    rows: filtered.slice((page - 1) * BATCH_PAGE_SIZE, page * BATCH_PAGE_SIZE),
    setSearch: filter(changeSearch),
    setProgram: filter(changeProgram),
    setYear: filter(changeYear),
    setStatus: filter(changeStatus),
    setSort: filter(changeSort),
    setPage,
    clearFilters,
  }
}
export type BatchesState = ReturnType<typeof useBatches>

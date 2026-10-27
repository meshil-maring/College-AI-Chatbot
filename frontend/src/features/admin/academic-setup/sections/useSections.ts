import { useState } from 'react'
import { SECTION_PAGE_SIZE, filterSections, type SectionRecord, type SectionSort } from './sectionModel.ts'
import { sectionChoices, storedSection } from './sectionStorage.ts'
import { useAcademicStructure, type StructureContext } from '../structure/useAcademicStructure.ts'
import { useStructureWrite } from '../structure/useStructureWrite.ts'

export function useSections(context: StructureContext) {
  const source = useAcademicStructure(context)
  const write = useStructureWrite(source, 'academic_sections')
  const records = (source.structure?.records.academic_sections ?? []).map(storedSection)
  const choices = sectionChoices(source)
  const [search, changeSearch] = useState('')
  const [batch, changeBatch] = useState('')
  const [program, changeProgram] = useState('')
  const [year, changeYear] = useState('')
  const [status, changeStatus] = useState('')
  const [sort, changeSort] = useState<SectionSort>('reference')
  const [requestedPage, setPage] = useState(1)
  const [notice, setNotice] = useState('')
  const filtered = filterSections(records, choices.batches, { search, batch, program, year, status, sort })
  const pages = Math.max(1, Math.ceil(filtered.length / SECTION_PAGE_SIZE))
  const page = Math.min(requestedPage, pages)
  function filter<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
    }
  }
  function clearFilters() {
    changeSearch('')
    changeBatch('')
    changeProgram('')
    changeYear('')
    changeStatus('')
    setPage(1)
  }
  async function save(record: SectionRecord, existing: boolean) {
    const payload = {
      name: record.name.trim(),
      capacity: record.capacity ? Number(record.capacity) : null,
      description: record.description.trim() || null,
      is_active: record.status === 'active',
    }
    const saved = await write.save(
      existing ? record.id : undefined,
      existing
        ? payload
        : {
            ...payload,
            code: record.code.trim(),
            admission_cohort_id: record.batchId,
            program_semester_id: record.programSemesterId,
            semester_id: record.semesterId,
          },
    )
    if (saved) {
      clearFilters()
      changeSort('reference')
      setNotice(`${record.name} ${existing ? 'updated' : 'created'} successfully.`)
    }
    return saved
  }
  const canManage = source.canManage('academic_sections')
  const canCreate =
    canManage &&
    choices.batches.some(
      (item) => item.active && choices.stages.some((stage) => stage.is_active && stage.program_id === item.programId),
    ) &&
    choices.terms.some((item) => item.available)
  return {
    ...source,
    source,
    ...choices,
    write,
    records,
    search,
    batch,
    program,
    year,
    status,
    sort,
    page,
    pages,
    filtered,
    notice,
    save,
    available: source.structure?.records.academic_sections !== undefined,
    canManage,
    canCreate,
    rows: filtered.slice((page - 1) * SECTION_PAGE_SIZE, page * SECTION_PAGE_SIZE),
    setSearch: filter(changeSearch),
    setBatch: filter(changeBatch),
    setProgram: filter(changeProgram),
    setYear: filter(changeYear),
    setStatus: filter(changeStatus),
    setSort: filter(changeSort),
    setPage,
    clearFilters,
  }
}
export type SectionsState = ReturnType<typeof useSections>

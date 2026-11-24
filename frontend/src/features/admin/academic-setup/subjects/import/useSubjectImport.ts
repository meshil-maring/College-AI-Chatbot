import { useMemo, useRef, useState } from 'react'
import { createAcademicRecord } from '../../../../../services/admin/academics.ts'
import { createStructureRecord } from '../../../../../services/admin/academicStructure.ts'
import { notification } from '../../../../../lib/notifications/notification.ts'
import type { AcademicCatalogue } from '../../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../../types/academicStructure.ts'
import { parseSubjectCsv, validateSubjectRows } from './subjectImportModel.ts'
import { runSubjectImport, type RowResult } from './runSubjectImport.ts'

interface Options {
  accessToken: string
  institutionId: string
  catalogue?: AcademicCatalogue
  structure?: StructureCatalogue
  refresh: () => Promise<unknown>
}

export function useSubjectImport({ accessToken, institutionId, catalogue, structure, refresh }: Options) {
  const [departmentId, setDepartmentId] = useState('')
  const [curriculumId, setCurriculumId] = useState('')
  const [raw, setRaw] = useState<ReturnType<typeof parseSubjectCsv>>()
  const [fileName, setFileName] = useState('')
  const [fileError, setFileError] = useState<string>()
  const [results, setResults] = useState(new Map<number, RowResult>())
  const [running, setRunning] = useState(false)
  const locked = useRef(false)

  const departments = (catalogue?.records.departments ?? []).filter(
    (item) => item.institution_id === institutionId && item.is_active,
  )
  const programIds = new Set(
    (catalogue?.records.programs ?? []).filter((item) => item.department_id === departmentId).map((p) => p.program_id),
  )
  const curricula = (structure?.records.curriculum_versions ?? []).filter(
    (item) => item.status === 'draft' && item.is_active && programIds.has(item.program_id),
  )
  const curriculum = curricula.find((item) => item.curriculum_version_id === curriculumId)
  const courses = catalogue?.records.courses
  const totalSemesters = curriculum?.total_semesters ?? null
  const rows = useMemo(() => {
    if (!raw) return []
    const existing = (courses ?? []).filter((item) => item.department_id === departmentId)
    return validateSubjectRows(raw, existing, totalSemesters)
  }, [raw, courses, departmentId, totalSemesters])
  const valid = rows.filter((row) => !row.errors.length)
  const failed = valid.filter((row) => results.get(row.sourceRow)?.status === 'failed')
  const done = valid.filter((row) => results.get(row.sourceRow)?.status === 'done')

  async function chooseFile(file: File | undefined) {
    setResults(new Map())
    setFileError(undefined)
    setRaw(undefined)
    setFileName(file?.name ?? '')
    if (!file) return
    try {
      setRaw(parseSubjectCsv(await file.text()))
    } catch (cause) {
      setFileError(cause instanceof Error ? cause.message : 'Could not read this file.')
    }
  }

  async function start() {
    if (locked.current || !departmentId || !valid.length) return
    locked.current = true
    setRunning(true)
    try {
      const final = await runSubjectImport(
        rows,
        {
          departmentId,
          curriculum,
          stages: (structure?.records.program_semesters ?? []).filter((s) => s.program_id === curriculum?.program_id),
          mappings: (structure?.records.curriculum_subjects ?? []).filter(
            (m) => m.curriculum_version_id === curriculumId,
          ),
        },
        {
          createCourse: (payload) => createAcademicRecord(accessToken, 'courses', payload),
          createStage: (payload) => createStructureRecord(accessToken, 'program_semesters', payload),
          createMapping: (payload) => createStructureRecord(accessToken, 'curriculum_subjects', payload),
        },
        results,
        setResults,
      )
      await refresh()
      const failures = [...final.values()].filter((item) => item.status === 'failed').length
      if (failures) notification.error(`${failures} row${failures === 1 ? '' : 's'} could not be imported.`)
      else notification.success('Subjects imported successfully')
    } finally {
      locked.current = false
      setRunning(false)
    }
  }

  return {
    departments,
    departmentId,
    setDepartmentId: (id: string) => {
      setDepartmentId(id)
      setCurriculumId('')
      setResults(new Map())
    },
    curricula,
    curriculumId,
    setCurriculumId: (id: string) => {
      setCurriculumId(id)
      setResults(new Map())
    },
    fileName,
    fileError,
    rows,
    valid,
    failed,
    done,
    results,
    running,
    chooseFile,
    start,
  }
}
export type SubjectImportState = ReturnType<typeof useSubjectImport>

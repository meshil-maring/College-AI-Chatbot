import { useRef, useState } from 'react'
import { createAcademicRecord } from '../../../../services/admin/academics.ts'
import { createStructureRecord, updateStructureRecord } from '../../../../services/admin/academicStructure.ts'
import { useAcademicStructure, type StructureContext } from '../structure/useAcademicStructure.ts'
import { QUICK_SETUP_STEPS, type QuickSetupStep } from './quickSetupModel.ts'

const DEPENDENTS = {
  department: ['program', 'curriculum', 'batch'],
  program: ['curriculum', 'batch'],
  year: ['batch'],
  curriculum: ['batch'],
  batch: [],
} as const

export function useQuickSetup(context: StructureContext) {
  const state = useAcademicStructure(context)
  const [step, setStep] = useState<QuickSetupStep>('department')
  const [ids, setIds] = useState({ department: '', program: '', year: '', curriculum: '', batch: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>()
  const locked = useRef(false)
  const base = state.catalogue?.records
  const records = state.structure?.records
  const own = <T extends { institution_id: string; is_active: boolean }>(items?: T[]) =>
    (items ?? []).filter((item) => item.institution_id === context.institutionId && item.is_active)

  const departments = own(base?.departments)
  const programs = own(base?.programs).filter((item) => item.department_id === ids.department)
  const program = programs.find((item) => item.program_id === ids.program)
  const years = own(base?.academic_years).sort((a, b) => b.start_date.localeCompare(a.start_date))
  const year = years.find((item) => item.academic_year_id === ids.year)
  const terms = own(base?.semesters)
    .filter((item) => item.academic_year_id === ids.year)
    .sort((a, b) => a.semester_number - b.semester_number)
  const curricula = own(records?.curriculum_versions).filter(
    (item) => item.program_id === ids.program && item.status !== 'archived',
  )
  const curriculum = curricula.find((item) => item.curriculum_version_id === ids.curriculum)
  const stages = own(records?.program_semesters)
    .filter((item) => item.program_id === ids.program)
    .sort((a, b) => a.semester_number - b.semester_number)
  const mappings = own(records?.curriculum_subjects).filter((item) => item.curriculum_version_id === ids.curriculum)
  const batches = own(records?.admission_cohorts).filter((item) => item.program_id === ids.program)

  /** Runs one step's writes once at a time, refreshes, and keeps the error for the step to show. */
  async function perform(action: () => Promise<void>, next?: QuickSetupStep) {
    if (locked.current) return false
    locked.current = true
    setSaving(true)
    setError(undefined)
    try {
      await action()
      await state.refresh()
      if (next) setStep(next)
      return true
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this step.')
      await state.refresh()
      return false
    } finally {
      locked.current = false
      setSaving(false)
    }
  }

  const token = context.accessToken
  return {
    loading: state.loading,
    canManage:
      Boolean(state.catalogue?.manageable.includes('departments')) &&
      Boolean(state.catalogue?.manageable.includes('courses')) &&
      state.canManage('curriculum_versions') &&
      state.canManage('academic_sections'),
    step,
    stepIndex: QUICK_SETUP_STEPS.findIndex((item) => item.id === step),
    goTo: (target: QuickSetupStep) => {
      setError(undefined)
      setStep(target)
    },
    ids,
    choose: (key: keyof typeof ids, value: string) => {
      setError(undefined)
      setIds((current) => {
        // Only choices that depend on this one are cleared; the academic year is shared by every program.
        const reset = DEPENDENTS[key]
        return { ...current, [key]: value, ...Object.fromEntries(reset.map((item) => [item, ''])) }
      })
    },
    saving,
    error,
    perform,
    data: {
      departments,
      programs,
      program,
      years,
      year,
      terms,
      curricula,
      curriculum,
      stages,
      mappings,
      batches,
      records,
    },
    api: {
      createAcademic: <E extends Parameters<typeof createAcademicRecord>[1]>(
        entity: E,
        payload: Parameters<typeof createAcademicRecord<E>>[2],
      ) => createAcademicRecord(token, entity, payload),
      createStructure: <E extends Parameters<typeof createStructureRecord>[1]>(
        entity: E,
        payload: Parameters<typeof createStructureRecord<E>>[2],
      ) => createStructureRecord(token, entity, payload),
      publish: (id: string) => updateStructureRecord(token, 'curriculum_versions', id, { status: 'published' }),
    },
    importOptions: {
      accessToken: token,
      institutionId: context.institutionId,
      catalogue: state.catalogue,
      structure: state.structure,
      refresh: state.refresh,
    },
  }
}
export type QuickSetupState = ReturnType<typeof useQuickSetup>

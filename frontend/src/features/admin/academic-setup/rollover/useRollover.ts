import { useMemo, useRef, useState } from 'react'
import { createAcademicRecord } from '../../../../services/admin/academics.ts'
import { createStructureRecord } from '../../../../services/admin/academicStructure.ts'
import { notification } from '../../../../lib/notifications/notification.ts'
import { useAcademicStructure, type StructureContext } from '../structure/useAcademicStructure.ts'
import { planHasWork, planRollover } from './rolloverPlan.ts'
import { runRollover, type RolloverProgress } from './runRollover.ts'

const NEEDED = ['program_semesters', 'academic_sections', 'academic_offerings'] as const

export function useRollover(context: StructureContext) {
  const state = useAcademicStructure(context)
  const years = useMemo(
    () =>
      (state.catalogue?.records.academic_years ?? [])
        .filter((year) => year.institution_id === context.institutionId && year.is_active)
        .sort((a, b) => b.start_date.localeCompare(a.start_date)),
    [state.catalogue, context.institutionId],
  )
  const defaultYear = years.find((year) => year.is_current) ?? years[0]
  const [chosen, setChosen] = useState('')
  const sourceId = chosen || defaultYear?.academic_year_id || ''
  const plan = useMemo(
    () => (state.catalogue && state.structure ? planRollover(sourceId, state.catalogue, state.structure) : undefined),
    [sourceId, state.catalogue, state.structure],
  )
  const [progress, setProgress] = useState<RolloverProgress>()
  const [error, setError] = useState<string>()
  const [running, setRunning] = useState(false)
  const locked = useRef(false)
  const manageable = state.catalogue?.manageable ?? []
  const canRun =
    manageable.includes('academic_years') &&
    manageable.includes('semesters') &&
    NEEDED.every((entity) => state.canManage(entity))

  async function run() {
    if (locked.current || !plan || !canRun) return
    locked.current = true
    setRunning(true)
    setError(undefined)
    const token = context.accessToken
    try {
      const result = await runRollover(
        plan,
        {
          createYear: (payload) => createAcademicRecord(token, 'academic_years', payload),
          createTerm: (payload) => createAcademicRecord(token, 'semesters', payload),
          createStage: (payload) => createStructureRecord(token, 'program_semesters', payload),
          createSection: (payload) => createStructureRecord(token, 'academic_sections', payload),
          createOffering: (payload) => createStructureRecord(token, 'academic_offerings', payload),
        },
        setProgress,
      )
      notification.success('Next year is ready', `${result.done} records created.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The roll-over stopped.')
    } finally {
      // A fresh plan reuses everything that now exists, so Retry only creates what is missing.
      await state.refresh()
      locked.current = false
      setRunning(false)
    }
  }

  return {
    loading: state.loading,
    years,
    sourceId,
    setSourceId: (id: string) => {
      setChosen(id)
      setError(undefined)
      setProgress(undefined)
    },
    plan,
    hasWork: plan ? planHasWork(plan) : false,
    canRun,
    running,
    progress,
    error,
    run,
  }
}
export type RolloverState = ReturnType<typeof useRollover>

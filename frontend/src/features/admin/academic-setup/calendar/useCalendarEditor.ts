import { useEffect, useRef, useState } from 'react'
import type { AcademicYear, Semester } from '../../../../types/academicSetup.ts'
import {
  calendarDraft,
  makeSemesters,
  validateCalendar,
  type CalendarDraft,
  type CalendarErrors,
  type CalendarPanel,
} from './editor/calendarDraft.ts'
import { saveCalendar, type CalendarProgress } from './editor/saveCalendar.ts'
import type { CalendarContext, CalendarState } from './useCalendar.ts'

export function useCalendarEditor(context: CalendarContext, state: CalendarState) {
  const [panel, setPanel] = useState<CalendarPanel | null>(null)
  const [draft, setDraft] = useState(calendarDraft)
  const [errors, setErrors] = useState<CalendarErrors>({})
  const [validationVersion, setValidationVersion] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [confirmation, setConfirmation] = useState<'discard' | 'status' | null>(null)
  const [progress, setProgress] = useState<CalendarProgress>({ completed: 0 })
  const progressRef = useRef(progress)
  const initial = useRef('')
  const mounted = useRef(true)
  const submitting = useRef(false)
  const currentState = useRef(state)
  currentState.current = state
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  function allowed(entity: CalendarPanel['entity']) {
    const current = currentState.current
    return !current.busy && (entity === 'academic_years' ? current.canManageYears : current.canManageSemesters)
  }
  function panelAvailable(selected: CalendarPanel) {
    if (!allowed(selected.entity)) return false
    if (!selected.record) return selected.mode === 'add'
    const record = selected.record
    return 'semester_id' in record
      ? Boolean(currentState.current.semesters?.some((item) => item.semester_id === record.semester_id))
      : Boolean(currentState.current.years?.some((item) => item.academic_year_id === record.academic_year_id))
  }
  function open(
    entity: CalendarPanel['entity'],
    mode: CalendarPanel['mode'],
    record?: AcademicYear | Semester,
    parent?: AcademicYear,
  ) {
    if (submitting.current || (mode !== 'view' && !allowed(entity))) return
    const requested = record
    const selected =
      requested &&
      (entity === 'semesters' && 'semester_id' in requested
        ? state.semesters?.find((item) => item.semester_id === requested.semester_id)
        : entity === 'academic_years' && !('semester_id' in requested)
          ? state.years?.find((item) => item.academic_year_id === requested.academic_year_id)
          : undefined)
    if (mode !== 'add' && !selected) return
    record = selected
    const next = calendarDraft(record, parent)
    if (entity === 'semesters' && mode === 'add') {
      next.academic_year_id =
        parent?.academic_year_id ?? state.years?.find((item) => item.is_active)?.academic_year_id ?? ''
      const year = state.years?.find((item) => item.academic_year_id === next.academic_year_id)
      next.start_date = year?.start_date ?? next.start_date
      next.end_date = year?.end_date ?? next.end_date
      next.semester_number =
        Math.max(
          0,
          ...(state.semesters ?? [])
            .filter((item) => item.academic_year_id === next.academic_year_id)
            .map((item) => item.semester_number),
        ) + 1
      next.name = `Semester ${next.semester_number}`
      next.code = `S${next.semester_number}`
    }
    setPanel({ entity, mode, record })
    setDraft(next)
    initial.current = JSON.stringify(next)
    setErrors({})
    setError(null)
    setNotice(null)
    setConfirmation(null)
    progressRef.current = { completed: 0 }
    setProgress(progressRef.current)
  }
  function change<K extends keyof CalendarDraft>(field: K, value: CalendarDraft[K]) {
    setDraft((current) => {
      const next = { ...current, [field]: value }
      if (
        panel?.entity === 'academic_years' &&
        panel.mode === 'add' &&
        !progress.year &&
        ['start_date', 'end_date', 'plan'].includes(field) &&
        next.plan !== 'custom'
      )
        next.semesters = makeSemesters(next.start_date, next.end_date, Number(next.plan))
      return next
    })
    setErrors((current) => ({ ...current, [field]: undefined }))
    setError(null)
  }
  function close() {
    if (submitting.current) return
    const unfinished = progressRef.current.year && progressRef.current.completed < draft.semesters.length
    if (panel?.mode !== 'view' && (unfinished || JSON.stringify(draft) !== initial.current)) setConfirmation('discard')
    else setPanel(null)
  }
  async function submit(confirmed = false) {
    if (!panel || panel.mode === 'view' || submitting.current || !panelAvailable(panel)) return
    const includeSemesters = panel.entity === 'academic_years' && panel.mode === 'add' && state.canManageSemesters
    const nextErrors = validateCalendar(draft, panel, state.years ?? [], includeSemesters)
    if (
      panel.entity === 'semesters' &&
      state.semesters?.some(
        (item) =>
          item.academic_year_id === draft.academic_year_id &&
          item.semester_number === draft.semester_number &&
          item.semester_id !== (panel.record && 'semester_id' in panel.record ? panel.record.semester_id : undefined),
      )
    )
      nextErrors.semester_number = 'This semester number is already in use in this academic year.'
    setErrors(nextErrors)
    setValidationVersion((value) => value + 1)
    if (Object.keys(nextErrors).length) return
    if (
      panel.record &&
      !confirmed &&
      (draft.is_active !== panel.record.is_active || draft.is_current !== panel.record.is_current)
    ) {
      setConfirmation('status')
      return
    }
    submitting.current = true
    setSaving(true)
    setError(null)
    setConfirmation(null)
    try {
      await saveCalendar({
        token: context.accessToken,
        institutionId: context.institutionId,
        panel,
        draft,
        includeSemesters,
        progress: progressRef.current,
        isAvailable: () =>
          mounted.current && panelAvailable(panel) && (!includeSemesters || currentState.current.canManageSemesters),
        onProgress: (next) => {
          progressRef.current = next
          if (mounted.current) setProgress(next)
        },
      })
      if (!mounted.current) return
      setPanel(null)
      setNotice(
        `${panel.entity === 'academic_years' ? 'Academic year' : 'Semester'} ${panel.mode === 'add' ? 'created' : 'updated'} successfully.`,
      )
      await state.query.refetch()
    } catch (cause) {
      if (!mounted.current) return
      setError(cause instanceof Error ? cause.message : 'Could not save this record.')
      if (progressRef.current.year) await state.query.refetch()
    } finally {
      submitting.current = false
      if (mounted.current) setSaving(false)
    }
  }
  return {
    panel,
    draft,
    errors,
    validationVersion,
    error,
    notice,
    saving,
    confirmation,
    progress,
    canManage: Boolean(panel && panelAvailable(panel)),
    open,
    change,
    close,
    submit,
    cancelConfirmation: () => setConfirmation(null),
    discard: () => {
      setConfirmation(null)
      setPanel(null)
    },
  }
}
export type CalendarEditor = ReturnType<typeof useCalendarEditor>

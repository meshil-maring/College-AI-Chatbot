import { useEffect, useRef, useState } from 'react'
import type { AcademicCreateMap, ProgramCourse } from '../../../../../types/academicSetup.ts'
import { createAcademicRecord, updateAcademicRecord } from '../../../../../services/admin/academics.ts'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import { useApiMutation } from '../../../../../hooks/useApiQuery.ts'
import type { CurriculumContext, CurriculumState } from '../useCurriculum.ts'
import { mappingDraft, validateMapping, type MappingDraft, type MappingErrors } from './mappingDraft.ts'

export function useMappingEditor(context: CurriculumContext, state: CurriculumState) {
  const [panel, setPanel] = useState<'add' | 'edit' | null>(null)
  const [record, setRecord] = useState<ProgramCourse>()
  const [draft, setDraft] = useState(mappingDraft)
  const [errors, setErrors] = useState<MappingErrors>({})
  const [validationVersion, setValidationVersion] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<'discard' | 'status' | null>(null)
  const initial = useRef(JSON.stringify(draft))
  const mounted = useRef(true)
  const submitting = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const mutation = useApiMutation<ProgramCourse, { id?: string; payload: AcademicCreateMap['program_courses'] }>({
    mutationFn: async ({ id, payload }) => {
      if (!mounted.current || !state.manageable || state.busy || (!id && !state.canAdd))
        throw new Error('Subject mapping changes are unavailable. Refresh and try again.')
      if (
        id &&
        !state.links?.some((link) => link.program_course_id === id && link.institution_id === context.institutionId)
      )
        throw new Error('This mapping is no longer available.')
      if (
        !id &&
        Object.keys(validateMapping({ ...payload, semester_id: payload.semester_id ?? '' }, state, false)).length
      )
        throw new Error('Select available program, subject and academic term records.')
      const { course_type, is_required, is_active } = payload
      const result = id
        ? await updateAcademicRecord(context.accessToken, 'program_courses', id, {
            course_type,
            is_required,
            is_active,
          })
        : await createAcademicRecord(context.accessToken, 'program_courses', payload)
      if (result.institution_id !== context.institutionId)
        throw new Error('The saved mapping could not be verified for this institution.')
      return result
    },
    onSuccess: async (_data, variables) => {
      if (!mounted.current) return
      setPanel(null)
      setNotice(variables.id ? 'Subject mapping updated successfully.' : 'Subject mapped successfully.')
      await state.query.refetch()
    },
    onError: (cause) => {
      if (!mounted.current) return
      setError(
        cause instanceof AdminApiError && cause.code === 'ACADEMIC_DUPLICATE'
          ? 'This subject mapping already exists. Choose another subject or term.'
          : cause instanceof Error
            ? cause.message
            : 'Could not save this mapping.',
      )
    },
    onSettled: () => {
      submitting.current = false
    },
  })
  function open(link?: ProgramCourse, semesterId?: string, toggle = false) {
    if (mutation.isPending || !state.manageable || state.busy || (!link && !state.canAdd)) return
    if (link && !state.links?.some((item) => item.program_course_id === link.program_course_id)) return
    const next = mappingDraft(state.selected?.program_id, semesterId, link)
    initial.current = JSON.stringify(next)
    setDraft(toggle ? { ...next, is_active: !next.is_active } : next)
    setPanel(link ? 'edit' : 'add')
    setRecord(link)
    setErrors({})
    setError(null)
    setNotice(null)
    setConfirmation(toggle ? 'status' : null)
  }
  function change<K extends keyof MappingDraft>(field: K, value: MappingDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
    setError(null)
  }
  function close() {
    if (mutation.isPending) return
    if (JSON.stringify(draft) !== initial.current) setConfirmation('discard')
    else setPanel(null)
  }
  function submit(confirmed = false) {
    if (submitting.current || mutation.isPending || !panel || !state.manageable || state.busy) return
    const nextErrors = validateMapping(draft, state, panel === 'edit')
    setErrors(nextErrors)
    setError(null)
    if (Object.keys(nextErrors).length) {
      setValidationVersion((value) => value + 1)
      return
    }
    if (record && draft.is_active !== record.is_active && !confirmed) {
      setConfirmation('status')
      return
    }
    setConfirmation(null)
    submitting.current = true
    mutation.mutate({
      id: panel === 'edit' ? record?.program_course_id : undefined,
      payload: { ...draft, semester_id: draft.semester_id || null },
    })
  }
  return {
    panel,
    record,
    draft,
    errors,
    validationVersion,
    error,
    notice,
    confirmation,
    saving: mutation.isPending,
    canManage: state.manageable && !state.busy && (panel !== 'add' || state.canAdd),
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
export type MappingEditor = ReturnType<typeof useMappingEditor>

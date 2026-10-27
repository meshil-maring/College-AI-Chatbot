import { useEffect, useRef, useState } from 'react'
import { useApiMutation } from '../../../../hooks/useApiQuery.ts'
import { createAcademicRecord, updateAcademicRecord } from '../../../../services/admin/academics.ts'
import { AdminApiError } from '../../../../services/admin/http.ts'
import type { AcademicCatalogue, AcademicCreateMap, Course } from '../../../../types/academicSetup.ts'
import { subjectDepartments } from './subjectModel.ts'
import { subjectDraft, validateSubject, type SubjectDraft, type SubjectErrors } from './forms/subjectDraft.ts'

interface Options {
  accessToken: string
  institutionId: string
  catalogue?: AcademicCatalogue
  busy: boolean
  refresh: () => Promise<unknown>
}
export function useSubjectEditor({ accessToken, institutionId, catalogue, busy, refresh }: Options) {
  const [panel, setPanel] = useState<'add' | 'view' | 'edit' | null>(null)
  const [record, setRecord] = useState<Course | undefined>()
  const [draft, setDraft] = useState(subjectDraft)
  const [errors, setErrors] = useState<SubjectErrors>({})
  const [validationVersion, setValidationVersion] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<'discard' | 'status' | null>(null)
  const initial = useRef(JSON.stringify(subjectDraft()))
  const mounted = useRef(true)
  const submitting = useRef(false)
  const departments = subjectDepartments(catalogue, institutionId) ?? []
  const canManage =
    catalogue?.institution_id === institutionId &&
    catalogue.records.courses !== undefined &&
    catalogue.manageable.includes('courses')
  const canCreate = canManage && departments.some((item) => item.is_active)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const mutation = useApiMutation<Course, { id?: string; payload: AcademicCreateMap['courses'] }>({
    mutationFn: async ({ id, payload }) => {
      if (!mounted.current || !canManage || busy || (!id && !canCreate))
        throw new Error('Subject changes are unavailable. Refresh and try again.')
      if (
        id &&
        !catalogue?.records.courses?.some((item) => item.course_id === id && item.institution_id === institutionId)
      )
        throw new Error('This subject is no longer available.')
      const { department_id, ...changes } = payload
      if (!id && !departments.some((item) => item.department_id === department_id && item.is_active))
        throw new Error('Select an available active department.')
      // The parent department is immutable in the existing update contract.
      const result = id
        ? await updateAcademicRecord(accessToken, 'courses', id, changes)
        : await createAcademicRecord(accessToken, 'courses', payload)
      if (result.institution_id !== institutionId)
        throw new Error('The saved subject could not be verified for this institution.')
      return result
    },
    onSuccess: async (_data, variables) => {
      if (!mounted.current) return
      setPanel(null)
      setNotice(variables.id ? 'Subject updated successfully.' : 'Subject created successfully.')
      await refresh()
    },
    onError: (cause) => {
      if (!mounted.current) return
      if (cause instanceof AdminApiError && cause.code === 'ACADEMIC_DUPLICATE') {
        setErrors({ code: 'This subject code is already in use in your institution.' })
        setValidationVersion((value) => value + 1)
      } else setError(cause instanceof Error ? cause.message : 'Could not save subject. Your entries have been kept.')
    },
    onSettled: () => {
      submitting.current = false
    },
  })

  function open(mode: 'add' | 'view' | 'edit', selected?: Course) {
    if (mutation.isPending || (mode !== 'view' && (!canManage || busy)) || (mode === 'add' && !canCreate)) return
    if (
      mode !== 'add' &&
      (!selected ||
        !catalogue?.records.courses?.some(
          (item) => item.course_id === selected.course_id && item.institution_id === institutionId,
        ))
    )
      return
    const next = subjectDraft(selected)
    setPanel(mode)
    setRecord(selected)
    setDraft(next)
    initial.current = JSON.stringify(next)
    setErrors({})
    setError(null)
    setNotice(null)
    setConfirmation(null)
  }
  function change<K extends keyof SubjectDraft>(field: K, value: SubjectDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
    setError(null)
  }
  function close() {
    if (mutation.isPending) return
    if (panel !== 'view' && JSON.stringify(draft) !== initial.current) setConfirmation('discard')
    else setPanel(null)
  }
  function submit(confirmed = false) {
    if (submitting.current || mutation.isPending || !canManage || busy || !panel || panel === 'view') return
    const nextErrors = validateSubject(draft, departments, panel === 'edit')
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
      id: panel === 'edit' ? record?.course_id : undefined,
      payload: {
        name: draft.name.trim(),
        code: draft.code.trim(),
        department_id: draft.department_id,
        credits: draft.credits.trim() ? Number(draft.credits) : null,
        lecture_hours: draft.lecture_hours.trim() ? Number(draft.lecture_hours) : null,
        tutorial_hours: draft.tutorial_hours.trim() ? Number(draft.tutorial_hours) : null,
        practical_hours: draft.practical_hours.trim() ? Number(draft.practical_hours) : null,
        description: draft.description.trim() || null,
        is_active: draft.is_active,
      },
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
    canManage: Boolean(canManage) && !busy && (panel !== 'add' || Boolean(canCreate)),
    saving: mutation.isPending,
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
export type SubjectEditor = ReturnType<typeof useSubjectEditor>

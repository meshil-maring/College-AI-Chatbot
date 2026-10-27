import { useEffect, useRef, useState } from 'react'
import { useApiMutation } from '../../../../hooks/useApiQuery.ts'
import { createAcademicRecord, updateAcademicRecord } from '../../../../services/admin/academics.ts'
import { AdminApiError } from '../../../../services/admin/http.ts'
import type { AcademicCatalogue, AcademicCreateMap, Department } from '../../../../types/academicSetup.ts'
import { departmentDraft, validateDepartment, type DepartmentDraft, type DepartmentErrors } from './departmentModel.ts'

interface Options {
  accessToken: string
  institutionId: string
  catalogue?: AcademicCatalogue
  busy: boolean
  refresh: () => Promise<unknown>
}
export function useDepartmentEditor({ accessToken, institutionId, catalogue, busy, refresh }: Options) {
  const [panel, setPanel] = useState<'add' | 'view' | 'edit' | null>(null)
  const [record, setRecord] = useState<Department | undefined>()
  const [draft, setDraft] = useState(departmentDraft)
  const [errors, setErrors] = useState<DepartmentErrors>({})
  const [validationVersion, setValidationVersion] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<'discard' | 'status' | null>(null)
  const initial = useRef(JSON.stringify(departmentDraft()))
  const mounted = useRef(true)
  const submitting = useRef(false)
  const canManage =
    catalogue?.institution_id === institutionId &&
    catalogue.records.departments !== undefined &&
    catalogue.manageable.includes('departments')
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const mutation = useApiMutation<Department, { id?: string; payload: AcademicCreateMap['departments'] }>({
    mutationFn: async ({ id, payload }) => {
      if (!mounted.current || !canManage || busy)
        throw new Error('Department changes are unavailable. Refresh and try again.')
      if (
        id &&
        !catalogue?.records.departments?.some(
          (item) => item.department_id === id && item.institution_id === institutionId,
        )
      )
        throw new Error('This department is no longer available.')
      const result = id
        ? await updateAcademicRecord(accessToken, 'departments', id, payload)
        : await createAcademicRecord(accessToken, 'departments', payload)
      if (result.institution_id !== institutionId)
        throw new Error('The saved department could not be verified for this institution.')
      return result
    },
    onSuccess: async (_data, variables) => {
      if (!mounted.current) return
      setPanel(null)
      setNotice(variables.id ? 'Department updated successfully.' : 'Department created successfully.')
      await refresh()
    },
    onError: (cause) => {
      if (!mounted.current) return
      if (cause instanceof AdminApiError && cause.code === 'ACADEMIC_DUPLICATE') {
        setErrors({ code: 'This department code is already in use in your institution.' })
        setValidationVersion((value) => value + 1)
      } else
        setError(cause instanceof Error ? cause.message : 'Could not save department. Your entries have been kept.')
    },
    onSettled: () => {
      submitting.current = false
    },
  })

  function open(mode: 'add' | 'view' | 'edit', selected?: Department) {
    if (mutation.isPending || (mode !== 'view' && (!canManage || busy))) return
    if (selected && selected.institution_id !== institutionId) return
    const next = departmentDraft(selected)
    setPanel(mode)
    setRecord(selected)
    setDraft(next)
    initial.current = JSON.stringify(next)
    setErrors({})
    setError(null)
    setNotice(null)
    setConfirmation(null)
  }
  function change<K extends keyof DepartmentDraft>(field: K, value: DepartmentDraft[K]) {
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
    if (submitting.current || mutation.isPending || !canManage || busy || panel === 'view') return
    const nextErrors = validateDepartment(draft)
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
      id: panel === 'edit' ? record?.department_id : undefined,
      payload: {
        name: draft.name.trim(),
        code: draft.code.trim(),
        description: draft.description.trim() || null,
        is_active: draft.is_active!,
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
    canManage: Boolean(canManage) && !busy,
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
export type DepartmentEditor = ReturnType<typeof useDepartmentEditor>

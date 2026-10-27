import { useRef, useState } from 'react'
import {
  emptySection,
  sectionDraft,
  validateSection,
  type SectionDraft,
  type SectionRecord,
  type SectionStatus,
} from '../sectionModel.ts'
import type { SectionsState } from '../useSections.ts'

export function useSectionEditor(state: SectionsState) {
  const [panel, setPanel] = useState<{ mode: 'add' | 'view' | 'edit'; record?: SectionRecord }>()
  const [draft, setDraft] = useState(emptySection)
  const [confirmation, setConfirmation] = useState<'discard' | 'status'>()
  const [error, setError] = useState<string>()
  const initial = useRef(JSON.stringify(emptySection()))
  function open(mode: 'add' | 'view' | 'edit', record?: SectionRecord, status?: SectionStatus) {
    if (state.write.saving || (mode !== 'view' && !state.canManage)) return
    const next = record ? sectionDraft(record) : emptySection()
    initial.current = JSON.stringify(next)
    setDraft(status ? { ...next, status } : next)
    setError(undefined)
    setConfirmation(undefined)
    setPanel({ mode, record })
  }
  function change<K extends keyof SectionDraft>(field: K, value: SectionDraft[K]) {
    if (state.write.saving) return
    state.write.clearError()
    setDraft((current) => ({
      ...current,
      [field]: value,
      ...(field === 'batchId' && value !== current.batchId ? { programSemesterId: '' } : {}),
    }))
    setError(undefined)
  }
  function close() {
    if (state.write.saving) return
    if (panel?.mode !== 'view' && JSON.stringify(draft) !== initial.current) setConfirmation('discard')
    else setPanel(undefined)
  }
  async function commit() {
    const saved = await state.save(
      {
        ...draft,
        name: draft.name.trim(),
        code: draft.code.trim(),
        description: draft.description.trim(),
        id: panel?.record?.id ?? '',
        studentCount: panel?.record?.studentCount ?? null,
        color: panel?.record?.color ?? 'gold',
      },
      Boolean(panel?.record),
    )
    if (!saved) return
    setPanel(undefined)
    setConfirmation(undefined)
  }
  function submit() {
    if (!panel || panel.mode === 'view' || state.write.saving || !state.canManage) return
    const batch = state.batches.find((item) => item.id === draft.batchId)
    const missingParent =
      !state.stages.some(
        (stage) => stage.program_semester_id === draft.programSemesterId && stage.program_id === batch?.programId,
      ) || !state.terms.some((term) => term.semester_id === draft.semesterId)
    const issue =
      validateSection(draft, state.records, state.batches, panel.record?.id) ??
      (!panel.record && missingParent ? 'Select a matching program semester and teaching term.' : undefined)
    if (issue) {
      setError(issue)
      return
    }
    if (panel.record && draft.status !== panel.record.status) setConfirmation('status')
    else void commit()
  }
  return {
    panel,
    draft,
    confirmation,
    error: error ?? state.write.error,
    saving: state.write.saving,
    state,
    open,
    change,
    close,
    submit,
    keepEditing: () => {
      if (!state.write.saving) setConfirmation(undefined)
    },
    confirm: () => {
      if (state.write.saving) return
      if (confirmation === 'status') void commit()
      else {
        setPanel(undefined)
        setConfirmation(undefined)
      }
    },
  }
}
export type SectionEditor = ReturnType<typeof useSectionEditor>

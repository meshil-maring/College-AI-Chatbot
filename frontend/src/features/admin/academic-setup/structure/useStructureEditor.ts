import { useRef, useState } from 'react'
import type { StructureCreateMap, StructureEntity, StructureUpdateMap } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'
import { useStructureWrite } from './useStructureWrite.ts'
import { structureCanEdit } from './structureAvailability.ts'
import { structureFields, type StructureDraft } from './structureFields.ts'
import {
  structureDraft,
  structureId,
  structurePayload,
  validateStructureFields,
  type StructureRow,
} from './structureForm.ts'

export function useStructureEditor(
  state: AcademicStructureState,
  entity: StructureEntity,
  defaults: StructureDraft = {},
) {
  const write = useStructureWrite(state, entity)
  const [panel, setPanel] = useState<{ mode: 'add' | 'edit' | 'view'; row?: StructureRow }>()
  const [draft, setDraft] = useState(() => structureDraft(undefined, defaults))
  const [error, setError] = useState<string>()
  const [confirmation, setConfirmation] = useState<'discard' | 'status'>()
  const [notice, setNotice] = useState('')
  const initial = useRef(JSON.stringify(draft))
  const fields = structureFields(entity, state, draft).map((field) => ({
    ...field,
    frozen:
      entity === 'curriculum_versions' && panel?.row && 'status' in panel.row && panel.row.status !== 'draft'
        ? field.key !== 'status'
        : false,
  }))
  function open(mode: 'add' | 'edit' | 'view', row?: StructureRow) {
    if (write.saving || (mode !== 'view' && !state.canManage(entity))) return
    if (mode === 'edit' && row && !structureCanEdit(entity, row, state)) return
    const next = structureDraft(row, defaults)
    setDraft(next)
    initial.current = JSON.stringify(next)
    setError(undefined)
    write.clearError()
    setConfirmation(undefined)
    setPanel({ mode, row })
  }
  function change(key: string, value: string | boolean) {
    if (write.saving) return
    setDraft((current) => ({
      ...current,
      [key]: value,
      ...(key === 'curriculum_version_id' ? { program_semester_id: '' } : {}),
      ...(key === 'academic_section_id' ? { curriculum_subject_id: '' } : {}),
    }))
    setError(undefined)
    write.clearError()
  }
  function close() {
    if (write.saving) return
    if (panel?.mode !== 'view' && JSON.stringify(draft) !== initial.current) setConfirmation('discard')
    else setPanel(undefined)
  }
  async function submit(confirmed = false) {
    if (!panel || panel.mode === 'view' || write.saving || !state.canManage(entity)) return
    if (panel.row && !structureCanEdit(entity, panel.row, state)) return
    const issue = validateStructureFields(fields, draft, panel.row)
    if (issue) {
      setError(issue)
      return
    }
    const payload = structurePayload(fields, draft, panel.row)
    if (!Object.keys(payload).length) {
      setPanel(undefined)
      return
    }
    if (!confirmed && panel.row && ['is_active', 'status'].some((key) => key in payload)) {
      setConfirmation('status')
      return
    }
    setConfirmation(undefined)
    const saved = await write.save(
      panel.row ? structureId(entity, panel.row) : undefined,
      payload as StructureCreateMap[StructureEntity] | StructureUpdateMap[StructureEntity],
    )
    if (saved) {
      setPanel(undefined)
      setNotice('Changes saved successfully.')
    }
  }
  return {
    panel,
    draft,
    fields,
    confirmation,
    notice,
    saving: write.saving,
    error: error ?? write.error,
    canManage: panel?.row ? structureCanEdit(entity, panel.row, state) : state.canManage(entity),
    open,
    change,
    close,
    submit,
    keepEditing: () => {
      if (!write.saving) setConfirmation(undefined)
    },
    confirm: () => {
      if (write.saving) return
      if (confirmation === 'status') void submit(true)
      else {
        setPanel(undefined)
        setConfirmation(undefined)
      }
    },
  }
}
export type StructureEditor = ReturnType<typeof useStructureEditor>

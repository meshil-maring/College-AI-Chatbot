import { useState } from 'react'
import { deleteChoiceGroup, saveChoiceGroup } from '../../../../../services/academics/semesterRegistration.ts'
import type { ChoiceGroup } from '../../../../../types/semesterRegistration.ts'
import type { CurriculumVersion, ProgramSemester } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import type { RegistrationAdminState } from '../../registration/useRegistrationAdmin.ts'
import { studyPlanCanChange } from '../semester-plan/studyPlanModel.ts'
import { useChoiceEditor } from './useChoiceEditor.ts'
import { choiceValidation } from './choiceValidation.ts'

export function useSemesterChoices(
  structure: AcademicStructureState,
  state: RegistrationAdminState,
  version: CurriculumVersion,
  semester: ProgramSemester,
) {
  const scope = {
    curriculum_version_id: version.curriculum_version_id,
    program_semester_id: semester.program_semester_id,
  }
  const editor = useChoiceEditor(scope)
  const [open, setOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string>()
  const groups =
    state.data?.groups.filter(
      (group) =>
        group.institution_id === structure.context.institutionId &&
        group.curriculum_version_id === scope.curriculum_version_id &&
        group.program_semester_id === scope.program_semester_id,
    ) ?? []
  const canWrite = Boolean(
    state.data?.can_manage_choices &&
    !state.busy &&
    !structure.busy &&
    semester.is_active &&
    studyPlanCanChange(structure, version),
  )
  function close() {
    if (state.saving) return
    editor.reset()
    setOpen(false)
  }
  async function save() {
    if (
      !canWrite ||
      editor.draft.curriculum_version_id !== scope.curriculum_version_id ||
      editor.draft.program_semester_id !== scope.program_semester_id
    )
      return
    editor.showValidation()
    const available = structure.structure?.records.curriculum_subjects?.filter(
      (item) =>
        item.is_active &&
        !item.is_required &&
        item.curriculum_version_id === scope.curriculum_version_id &&
        item.program_semester_id === scope.program_semester_id,
    )
    if (choiceValidation(editor.draft, new Set(available?.map((item) => item.curriculum_subject_id))).length) return
    if (editor.editingId && !groups.some((group) => group.choice_group_id === editor.editingId)) return
    const saved = await state.save(async () => {
      const result = await saveChoiceGroup(structure.context.accessToken, editor.draft, editor.editingId)
      if (!result.choice_group_id || (editor.editingId && result.choice_group_id !== editor.editingId))
        throw new Error('The saved choice group could not be verified.')
      return result
    })
    if (saved) {
      editor.reset()
      setOpen(false)
    }
  }
  async function remove() {
    if (!canWrite || !deleteId || !groups.some((group) => group.choice_group_id === deleteId)) return
    if (
      await state.save(async () => {
        const result = await deleteChoiceGroup(structure.context.accessToken, deleteId)
        if (result.choice_group_id !== deleteId) throw new Error('The deleted choice group could not be verified.')
        return result
      })
    ) {
      if (editor.editingId === deleteId) close()
      setDeleteId(undefined)
    }
  }
  return {
    editor,
    groups,
    open,
    canWrite,
    deleteId,
    save,
    remove,
    close,
    add: () => {
      if (canWrite) {
        editor.reset()
        setOpen(true)
      }
    },
    edit: (group: ChoiceGroup) => {
      if (canWrite && groups.some((item) => item.choice_group_id === group.choice_group_id)) {
        editor.edit(group)
        setOpen(true)
      }
    },
    requestDelete: (id: string | undefined) => {
      if (!state.saving) setDeleteId(id)
    },
  }
}

import { useEffect } from 'react'
import type { CurriculumVersion, ProgramSemester } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import { useStructureEditor } from '../../structure/useStructureEditor.ts'
import StructureDrawer from '../../structure/StructureDrawer.tsx'
import { studyPlanCanChange } from '../semester-plan/studyPlanModel.ts'

export default function SemesterSettings({
  state,
  version,
  semester,
  trackDraft,
}: {
  state: AcademicStructureState
  version: CurriculumVersion
  semester: ProgramSemester
  trackDraft: (key: string, open: boolean) => void
}) {
  const editor = useStructureEditor(
    { ...state, canManage: (entity) => studyPlanCanChange(state, version) && state.canManage(entity) },
    'program_semesters',
  )
  const canManage = studyPlanCanChange(state, version) && editor.canManage
  const draftKey = `semester-settings-${semester.program_semester_id}`
  const open = Boolean(editor.panel)
  useEffect(() => {
    trackDraft(draftKey, open)
    return () => trackDraft(draftKey, false)
  }, [draftKey, open, trackDraft])
  return (
    <>
      <button
        type="button"
        className="academic-secondary-button"
        disabled={!canManage || editor.saving}
        onClick={() => editor.open('edit', semester)}
      >
        Semester settings <span className="sr-only">for Semester {semester.semester_number}</span>
      </button>
      {editor.panel && (
        <StructureDrawer
          entity="program_semesters"
          editor={{
            ...editor,
            canManage,
            fields: editor.fields.filter((field) => ['name', 'code', 'is_active'].includes(field.key)),
          }}
          description={`Semester ${semester.semester_number} is shared across this program. Changes affect all its curricula and classes. Its number and existing links stay the same.`}
          statusDescription="Changing this shared semester’s active status affects every curriculum and class that uses it. Existing records and links are retained."
        />
      )}
    </>
  )
}

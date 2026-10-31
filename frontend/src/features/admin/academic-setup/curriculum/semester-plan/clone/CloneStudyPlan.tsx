import type { CurriculumVersion } from '../../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../../structure/useAcademicStructure.ts'
import type { StudyPlanChoicesState } from '../useStudyPlanChoices.ts'
import CurriculumDrawerFrame from '../../editor/CurriculumDrawerFrame.tsx'
import { useCloneStudyPlan } from './useCloneStudyPlan.ts'

export default function CloneStudyPlan({
  state,
  source,
  choices,
  onCloned,
}: {
  state: AcademicStructureState
  source: CurriculumVersion
  choices: StudyPlanChoicesState
  onCloned: (id: string) => void
}) {
  const clone = useCloneStudyPlan(state, source, choices, onCloned)
  return (
    <>
      {clone.canClone && (
        <button type="button" className="academic-secondary-button" onClick={clone.show}>
          Clone as draft
        </button>
      )}
      {clone.open && (
        <CurriculumDrawerFrame
          title="Clone study plan"
          description={`Create an independent draft based on ${source.name} · v${source.version}. The original and its batch assignments will not change.`}
          busy={clone.saving}
          initialFocusSelector="input"
          onClose={clone.close}
          footer={
            <>
              <button type="button" className="academic-secondary-button" disabled={clone.saving} onClick={clone.close}>
                Cancel
              </button>
              <button
                type="button"
                className="academic-primary-button"
                disabled={
                  clone.saving ||
                  clone.partialDraft ||
                  !clone.name.trim() ||
                  !clone.version.trim() ||
                  !clone.academicYearId
                }
                onClick={() => void clone.clone()}
              >
                {clone.saving ? 'Cloning…' : 'Create draft copy'}
              </button>
            </>
          }
        >
          <label className="structure-field">
            Curriculum name
            <input value={clone.name} maxLength={160} onChange={(event) => clone.setName(event.target.value)} />
          </label>
          <label className="structure-field">
            Version
            <input value={clone.version} maxLength={32} onChange={(event) => clone.setVersion(event.target.value)} />
          </label>
          <label className="structure-field">
            Academic year
            <select value={clone.academicYearId} onChange={(event) => clone.setAcademicYearId(event.target.value)}>
              <option value="">Select an active academic year</option>
              {clone.years.map((year) => (
                <option key={year.academic_year_id} value={year.academic_year_id}>
                  {year.name}
                </option>
              ))}
            </select>
          </label>
          <p>Active and inactive subject mappings and saved student choice groups are copied into the new draft.</p>
          {clone.error && (
            <p className="curriculum-form-error" role="alert">
              {clone.error}
            </p>
          )}
        </CurriculumDrawerFrame>
      )}
    </>
  )
}

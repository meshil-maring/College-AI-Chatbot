import { ACADEMIC_DEFINITIONS } from '../academicSetupDefinitions.ts'
import { FOUNDATION_LABELS } from '../academicSetupStages.ts'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import type { AcademicSetupState } from '../useAcademicSetup.ts'

export default function AcademicSetupGuidance({
  state,
  onNavigate,
}: {
  state: AcademicSetupState
  onNavigate: (entity: AcademicEntity) => void
}) {
  if (!state.data) return null
  return (
    <div className="academic-stage-guidance">
      <p>{state.definition.help}</p>
      {state.missing.length > 0 && (
        <div id="academic-prerequisites" className="academic-prerequisites">
          <h3>Before adding {state.definition.label.toLowerCase()}</h3>
          <p>Create or activate the required records first. Records with inactive parents are unavailable.</p>
          {state.missing.map((entity) => (
            <div key={entity}>
              {state.data?.records[entity] !== undefined ? (
                <button
                  type="button"
                  className="academic-secondary"
                  disabled={state.busy || state.formOpen}
                  onClick={() => onNavigate(entity)}
                >
                  Open {FOUNDATION_LABELS[entity] ?? ACADEMIC_DEFINITIONS[entity].label}
                </button>
              ) : (
                <p>
                  Ask an administrator with access to {FOUNDATION_LABELS[entity] ?? entity} to complete this
                  prerequisite.
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

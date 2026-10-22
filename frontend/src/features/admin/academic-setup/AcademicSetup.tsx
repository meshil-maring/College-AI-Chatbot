import AcademicPackagesWorkspace from '../../academic-packages/AcademicPackagesWorkspace.tsx'
import AcademicFoundationStage from './ui/AcademicFoundationStage.tsx'
import AcademicSetupHeader from './ui/AcademicSetupHeader.tsx'
import AcademicSetupSteps from './ui/AcademicSetupSteps.tsx'
import { ACADEMIC_STAGES } from './academicSetupStages.ts'
import { useAcademicFlow } from './useAcademicFlow.ts'
import './styles/academic-setup.css'

export { ACADEMIC_DEFINITIONS } from './academicSetupDefinitions.ts'
export { usable } from './academicSetupModel.ts'

export default function AcademicSetup({ accessToken }: { accessToken: string }) {
  return <AcademicSetupFlow key={accessToken} accessToken={accessToken} />
}

function AcademicSetupFlow({ accessToken }: { accessToken: string }) {
  const { stage, setStage, entity, busy, setBusy, current, navigateEntity } = useAcademicFlow()
  return (
    <section className="academic-setup academic-flow" aria-label="Academic setup workspace">
      <AcademicSetupHeader />
      <AcademicSetupSteps stage={stage} busy={busy} onChange={setStage} />
      <header className="academic-stage-intro">
        <p>
          Step {ACADEMIC_STAGES.indexOf(current) + 1} of {ACADEMIC_STAGES.length}
        </p>
        <h2>{current.title}</h2>
        <p>{current.description}</p>
      </header>
      {'entities' in current ? (
        <AcademicFoundationStage
          key={stage}
          accessToken={accessToken}
          entities={current.entities}
          initialEntity={current.entities.some((item) => item === entity) ? entity : current.entities[0]}
          onEditingChange={setBusy}
          onNavigate={navigateEntity}
        />
      ) : (
        <AcademicPackagesWorkspace
          key={stage}
          accessToken={accessToken}
          embeddedView={stage as 'curricula' | 'classes' | 'assignments'}
          onBusyChange={setBusy}
          onCreateProgram={() => navigateEntity('programs')}
        />
      )}
      <footer className="academic-stage-footer">
        {busy && <p className="academic-muted">Save or cancel the current record before changing steps.</p>}
        <button
          type="button"
          className="academic-secondary"
          disabled={busy || stage === 'college'}
          onClick={() => setStage(ACADEMIC_STAGES[ACADEMIC_STAGES.indexOf(current) - 1].key)}
        >
          Previous step
        </button>
        {stage !== 'assignments' && (
          <button
            type="button"
            className="academic-primary"
            disabled={busy}
            onClick={() => setStage(ACADEMIC_STAGES[ACADEMIC_STAGES.indexOf(current) + 1].key)}
          >
            Next: {ACADEMIC_STAGES[ACADEMIC_STAGES.indexOf(current) + 1].title}
          </button>
        )}
      </footer>
    </section>
  )
}

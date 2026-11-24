import { useSubjectImport } from '../../subjects/import/useSubjectImport.ts'
import SubjectImportPanel from '../../subjects/import/SubjectImportPanel.tsx'
import { StepFrame } from '../StepFrame.tsx'
import type { QuickSetupState } from '../useQuickSetup.ts'

function SemesterCounts({ setup }: { setup: QuickSetupState }) {
  const { stages, mappings, curriculum } = setup.data
  const shown = stages.filter((stage) => stage.semester_number <= (curriculum?.total_semesters ?? 0))
  return (
    <ul className="quick-semesters" aria-label="Subjects per semester">
      {shown.map((stage) => {
        const count = mappings.filter((item) => item.program_semester_id === stage.program_semester_id).length
        return (
          <li key={stage.program_semester_id} className={count ? 'has-subjects' : undefined}>
            <strong>{stage.name}</strong>
            <span>
              {count} subject{count === 1 ? '' : 's'}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export function SubjectsStep({ setup }: { setup: QuickSetupState }) {
  const importing = useSubjectImport({
    ...setup.importOptions,
    fixed: { departmentId: setup.ids.department, curriculumId: setup.ids.curriculum },
  })
  const pending = importing.valid.length - importing.done.length
  return (
    <StepFrame
      setup={setup}
      title="Subjects"
      description="Upload the study plan as a CSV file: each row is a subject, and its semester column places it in the plan."
      onBack={() => setup.goTo('curriculum')}
      continueLabel="Continue to publish"
      continueDisabled={!setup.data.mappings.length || importing.running}
      onContinue={() => setup.goTo('publish')}
    >
      <SemesterCounts setup={setup} />
      <SubjectImportPanel state={importing} />
      {importing.rows.length > 0 && (
        <button
          type="button"
          className="academic-primary-button quick-inline-action"
          disabled={importing.running || pending === 0}
          onClick={() => void importing.start()}
        >
          {importing.running
            ? 'Importing…'
            : importing.failed.length
              ? `Retry ${importing.failed.length} failed row${importing.failed.length === 1 ? '' : 's'}`
              : `Import ${pending} row${pending === 1 ? '' : 's'}`}
        </button>
      )}
      <p className="quick-note">
        You can also add subjects one at a time later in Curriculum → Subjects by semester, including choice groups for
        electives.
      </p>
    </StepFrame>
  )
}

export function PublishStep({ setup }: { setup: QuickSetupState }) {
  const curriculum = setup.data.curriculum
  return (
    <StepFrame
      setup={setup}
      title="Publish the curriculum"
      description="Publishing makes the study plan read-only so batches can use it. Later changes are made in a new version."
      onBack={() => setup.goTo('subjects')}
      continueLabel={curriculum?.status === 'published' ? 'Continue' : 'Publish and continue'}
      continueDisabled={!curriculum || !setup.data.mappings.length}
      onContinue={() =>
        void setup.perform(async () => {
          if (curriculum && curriculum.status !== 'published') await setup.api.publish(curriculum.curriculum_version_id)
        }, 'batch')
      }
    >
      <p className="quick-note">
        <strong>
          {curriculum?.name} · v{curriculum?.version}
        </strong>{' '}
        has {setup.data.mappings.length} subject{setup.data.mappings.length === 1 ? '' : 's'}.
      </p>
      <SemesterCounts setup={setup} />
    </StepFrame>
  )
}

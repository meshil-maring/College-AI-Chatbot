import type { ReactNode } from 'react'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import StructureState from '../../structure/StructureState.tsx'
import SemesterCard from './SemesterCard.tsx'
import StudyPlanSteps from './StudyPlanSteps.tsx'
import StudyPlanPublication from './StudyPlanPublication.tsx'
import { scopeStudyPlanState, studyPlanCanChange, studyPlanSemesters } from './studyPlanModel.ts'
import '../../structure/styles/structure.css'
import '../styles/curriculum.css'
import './study-plan.css'
import { useStudyPlanChoices } from './useStudyPlanChoices.ts'
import ChoiceCatalogueState from '../choices/ChoiceCatalogueState.tsx'
import SemesterSetup from '../semesters/SemesterSetup.tsx'
import { usePrepareSemesters } from '../semesters/usePrepareSemesters.ts'

export default function SemesterPlanPage({
  state: source,
  versionId,
  onVersionChange,
  onOverview,
  onCreateCurriculum,
  onBatches,
  navigation,
}: {
  state: AcademicStructureState
  versionId: string
  onVersionChange: (id: string) => void
  onOverview: () => void
  onCreateCurriculum: () => void
  onBatches?: () => void
  navigation: ReactNode
}) {
  const scoped = scopeStudyPlanState(source)
  const choices = useStudyPlanChoices(scoped.context)
  const versions = scoped.structure?.records.curriculum_versions
  const version = versions?.find((item) => item.curriculum_version_id === versionId)
  const setup = usePrepareSemesters(scoped, version, choices.hasDrafts)
  const state = {
    ...scoped,
    busy: scoped.busy || setup.saving,
    canManage: (entity: Parameters<typeof scoped.canManage>[0]) => !setup.saving && scoped.canManage(entity),
  }
  const available = Boolean(
    state.structure?.records.program_semesters &&
    state.structure?.records.curriculum_subjects &&
    state.catalogue?.records.courses,
  )
  const program = state.catalogue?.records.programs?.find((item) => item.program_id === version?.program_id)
  return (
    <section
      className="academic-workspace curriculum-page structure-records-page study-plan-page"
      aria-label="Semester study plan"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <span aria-hidden="true">/</span>
        <span aria-current="page">Curriculum</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Subjects by semester</h1>
          <p>Set up semesters, then choose compulsory subjects and student choices in one place.</p>
        </div>
      </header>
      {navigation}
      <StudyPlanSteps subjects />
      <StructureState state={state} />
      {version && <ChoiceCatalogueState state={choices} />}
      {!state.loading && versions && !versions.length && (
        <div className="study-plan-guide">
          <p>Create a draft curriculum first. Then choose subjects for each semester here.</p>
          <button type="button" className="academic-primary-button" onClick={onCreateCurriculum}>
            Go to curriculum list
          </button>
        </div>
      )}
      {versions && versions.length > 0 && (
        <label className="structure-field study-plan-picker">
          Choose a curriculum
          <select
            value={version?.curriculum_version_id ?? ''}
            disabled={setup.saving}
            onChange={(event) => onVersionChange(event.target.value)}
          >
            <option value="">Select a study plan</option>
            {versions.map((item) => (
              <option key={item.curriculum_version_id} value={item.curriculum_version_id}>
                {state.catalogue?.records.programs?.find((entry) => entry.program_id === item.program_id)?.name ??
                  'Program unavailable'}{' '}
                · {item.name} · v{item.version} ({item.status})
              </option>
            ))}
          </select>
        </label>
      )}
      {!state.loading && !versions && !state.error && <p>Curriculum records are unavailable for your account.</p>}
      {versions?.length && !version ? <p>Select a curriculum above to see its semesters and subjects.</p> : null}
      {version && available && (
        <>
          <div className="study-plan-heading">
            <h2>{version.name}</h2>
            <p>
              {program?.name ?? 'Program unavailable'} · v{version.version} ·{' '}
              <span className={`structure-status ${version.status}`}>{version.status}</span>
            </p>
            {version.status !== 'draft' && (
              <p>
                This study plan is {version.status}. Its subjects are kept unchanged for existing batches. Create a new
                draft for changes.
              </p>
            )}
            {version.status === 'draft' && !version.is_active && (
              <p>This draft is inactive. Activate it in the curriculum list before adding subjects.</p>
            )}
            {version.status === 'draft' && version.is_active && !studyPlanCanChange(state, version) && (
              <p>
                The program, department or academic year is inactive or unavailable. Check them before changing this
                study plan.
              </p>
            )}
            {version.status === 'draft' && !state.structure?.manageable.includes('curriculum_subjects') && (
              <p>Read-only access to semester subjects. Your account cannot change this study plan.</p>
            )}
            {state.refreshing && <p role="status">Updating study plan…</p>}
          </div>
          {version.status === 'draft' && <SemesterSetup setup={setup} hasDrafts={choices.hasDrafts} />}
          <div className="study-plan-semesters" key={`semesters-${version.curriculum_version_id}`}>
            {studyPlanSemesters(state, version).map((item) => (
              <SemesterCard key={item.number} {...item} state={state} version={version} choices={choices} />
            ))}
          </div>
          <StudyPlanPublication
            key={`publication-${version.curriculum_version_id}`}
            state={state}
            version={version}
            onBatches={onBatches}
            choices={choices}
          />
        </>
      )}
      {version && !available && !state.loading && (
        <p>Semester or subject records are unavailable. Check your access or retry loading.</p>
      )}
    </section>
  )
}

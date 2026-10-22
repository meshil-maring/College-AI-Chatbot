import { useEffect } from 'react'
import { RefreshCw } from 'lucide-react'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import { useAcademicSetup } from '../useAcademicSetup.ts'
import { useAcademicDirectory } from '../useAcademicDirectory.ts'
import { FOUNDATION_LABELS } from '../academicSetupStages.ts'
import { records } from '../academicSetupModel.ts'
import AcademicRecordTable from './AcademicRecordTable.tsx'
import AcademicRecordDetail from './AcademicRecordDetail.tsx'
import AcademicRecordForm from './AcademicRecordForm.tsx'
import AcademicSetupGuidance from './AcademicSetupGuidance.tsx'

export default function AcademicFoundationStage({
  accessToken,
  entities,
  initialEntity,
  onEditingChange,
  onNavigate,
}: {
  accessToken: string
  entities: readonly AcademicEntity[]
  initialEntity: AcademicEntity
  onEditingChange: (editing: boolean) => void
  onNavigate: (entity: AcademicEntity) => void
}) {
  const state = useAcademicSetup(accessToken, initialEntity, entities)
  const directory = useAcademicDirectory(state.data, state.entity)
  useEffect(() => {
    onEditingChange(state.formOpen || state.busy)
  }, [state.formOpen, state.busy, onEditingChange])
  function navigate(entity: AcademicEntity) {
    if (entities.includes(entity)) {
      directory.resetFilters()
      state.reset(entity)
    } else onNavigate(entity)
  }
  return (
    <div>
      <div className="academic-stage-tools">
        {state.available.length > 1 && (
          <label>
            Manage
            <select
              aria-label="Record type"
              value={state.entity}
              disabled={state.formOpen || state.busy}
              onChange={(event) => navigate(event.target.value as AcademicEntity)}
            >
              {state.available.map((entity) => (
                <option key={entity} value={entity}>
                  {FOUNDATION_LABELS[entity]} · {state.activeCounts[entity]} active
                </option>
              ))}
            </select>
          </label>
        )}
        {state.entity === 'semesters' && state.data && (
          <label>
            Academic year
            <select
              aria-label="Academic year filter"
              value={directory.year}
              disabled={state.formOpen || state.busy}
              onChange={(event) => directory.setYear(event.target.value)}
            >
              <option value="">All academic years</option>
              {records(state.data, 'academic_years').map((row) => (
                <option key={String(row.academic_year_id)} value={String(row.academic_year_id)}>
                  {String(row.name)}
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          type="button"
          className="academic-secondary"
          aria-label="Refresh academic setup"
          disabled={state.query.isFetching || state.busy || state.formOpen}
          onClick={() => void state.query.refetch()}
        >
          <RefreshCw aria-hidden="true" /> Refresh
        </button>
      </div>
      {state.query.isPending && (
        <p role="status" className="academic-empty">
          Loading college records…
        </p>
      )}
      {state.query.isError && (
        <div role="alert" className="academic-error">
          <p>{state.query.error instanceof Error ? state.query.error.message : 'Could not load college records.'}</p>
          <button type="button" className="academic-secondary" onClick={() => void state.query.refetch()}>
            Retry loading
          </button>
        </div>
      )}
      {state.error && (
        <p role="alert" className="academic-error">
          {state.error}
        </p>
      )}
      {state.notice && (
        <p role="status" className="academic-success">
          {state.notice}
        </p>
      )}
      {state.data &&
        (state.available.length ? (
          <>
            <AcademicSetupGuidance state={state} onNavigate={navigate} />
            <div className="academic-columns">
              <AcademicRecordTable state={state} directory={directory} />
              {state.formOpen && state.canManage ? (
                <section className="academic-panel academic-form">
                  <AcademicRecordForm state={state} />
                </section>
              ) : (
                <AcademicRecordDetail state={state} row={directory.selected} onNavigate={navigate} />
              )}
            </div>
          </>
        ) : (
          <p className="academic-empty">Your role has no access to these college records.</p>
        ))}
    </div>
  )
}

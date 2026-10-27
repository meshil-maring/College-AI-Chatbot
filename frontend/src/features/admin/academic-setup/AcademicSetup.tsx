import { useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { ACADEMIC_HELP, ACADEMIC_LABELS } from './academicSetupForm.ts'
import AcademicSetupForm from './AcademicSetupForm.tsx'
import { academicButtonClass } from './forms/academicFormControls.ts'
import { academicParents } from './academicSetupParents.ts'
import AcademicSetupRecords from './AcademicSetupRecords.tsx'
import { useAcademicSetup } from './useAcademicSetup.ts'
import type { AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'
import AcademicTransitionDialog from './transitions/AcademicTransitionDialog.tsx'

interface Props {
  initialEntity?: AcademicEntity
  createInitially?: boolean
}

export default function AcademicSetup(props: Props) {
  const { accessToken, user, role } = useAuth()
  if (!accessToken || !user || role !== 'admin') return <p role="status">Administrator access is unavailable.</p>
  const identity = JSON.stringify([accessToken, user.user_id, user.institution_id, user.effective_permissions])
  // Identity changes remount all drafts and feedback; late mutations belong to the old instance.
  return <AcademicSetupWorkspace key={identity} accessToken={accessToken} identity={identity} {...props} />
}

function AcademicSetupWorkspace({
  accessToken,
  identity,
  initialEntity,
  createInitially,
}: Props & { accessToken: string; identity: string }) {
  const state = useAcademicSetup(accessToken, identity, initialEntity, createInitially)
  const [pendingTransition, setPendingTransition] = useState<AcademicRecord | null>(null)
  if (state.query.isPending) return <p role="status">Loading Academic Setup…</p>
  if (!state.query.data)
    return (
      <div className="space-y-3">
        <p role="alert">
          {state.query.error instanceof Error ? state.query.error.message : 'Could not load Academic Setup.'}
        </p>
        <button type="button" onClick={() => void state.query.refetch()} className={academicButtonClass}>
          Retry
        </button>
      </div>
    )
  if (!state.entities.length) return <p role="status">Your account has no readable academic catalogues.</p>
  const parents = academicParents(state.query.data, state.entity)
  return (
    <section aria-label="Academic Setup" className="space-y-4">
      <nav aria-label="Academic Setup pages" className="flex flex-wrap gap-2">
        {state.entities.map((entity) => (
          <button
            type="button"
            key={entity}
            aria-current={entity === state.entity ? 'page' : undefined}
            disabled={state.busy}
            onClick={() => {
              state.select(entity)
            }}
            className={`${academicButtonClass} ${entity === state.entity ? 'bg-emerald-800' : 'bg-slate-800'}`}
          >
            {ACADEMIC_LABELS[entity]}
          </button>
        ))}
      </nav>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-white">{ACADEMIC_LABELS[state.entity]}</h2>
        {state.manageable && (
          <button
            type="button"
            disabled={state.busy || parents.issue !== null}
            onClick={() => state.open()}
            className={`${academicButtonClass} bg-emerald-700`}
          >
            Add {state.singular}
          </button>
        )}
      </div>
      <p className="text-sm text-slate-300">{ACADEMIC_HELP[state.entity]}</p>
      {!state.manageable && <p className="text-sm text-slate-400">Read-only access.</p>}
      {state.manageable && parents.issue && <p className="text-sm text-amber-200">{parents.issue}</p>}
      {state.query.isError && (
        <div className="space-y-2">
          <p role="alert">Could not refresh Academic Setup. Retry before making further changes.</p>
          <button type="button" onClick={() => void state.query.refetch()} className={academicButtonClass}>
            Retry
          </button>
        </div>
      )}
      {state.error && (
        <p role="alert" className="rounded-lg border border-red-700 p-3 text-red-200">
          {state.error}
        </p>
      )}
      {state.notice && (
        <p role="status" className="text-emerald-300">
          {state.notice}
        </p>
      )}
      {state.formOpen && state.manageable && (
        <AcademicSetupForm
          entity={state.entity}
          singular={state.singular}
          editing={state.editing !== null}
          draft={state.draft}
          setDraft={state.setDraft}
          catalogue={parents.catalogue}
          busy={state.busy}
          onSave={state.save}
          onCancel={state.close}
        />
      )}
      <AcademicSetupRecords
        records={state.records}
        catalogue={parents.catalogue}
        manageable={state.manageable}
        busy={state.busy}
        onEdit={state.open}
        onToggle={setPendingTransition}
      />
      {pendingTransition && (
        <AcademicTransitionDialog
          record={pendingTransition}
          catalogue={parents.catalogue}
          onCancel={() => setPendingTransition(null)}
          onConfirm={() => {
            state.toggle(pendingTransition)
            setPendingTransition(null)
          }}
        />
      )}
    </section>
  )
}

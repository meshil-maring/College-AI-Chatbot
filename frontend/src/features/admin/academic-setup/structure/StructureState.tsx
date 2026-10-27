import type { AcademicStructureState } from './useAcademicStructure.ts'

export default function StructureState({ state }: { state: AcademicStructureState }) {
  if (state.loading) return <p role="status">Loading academic records…</p>
  if (state.error)
    return (
      <div className="academic-request-error" role="alert">
        <p>{state.error} Retained records may be out of date; changes are disabled.</p>
        <button
          type="button"
          className="academic-secondary-button"
          disabled={state.busy && !state.error}
          onClick={() => void state.refresh()}
        >
          Retry
        </button>
      </div>
    )
  if (!state.context.canReadCatalogues || state.denied)
    return <p role="status">Your account does not have academic catalogue access.</p>
  return null
}

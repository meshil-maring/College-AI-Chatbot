import type { RegistrationAdminState } from '../../registration/useRegistrationAdmin.ts'

export default function ChoiceCatalogueState({ state }: { state: RegistrationAdminState }) {
  return (
    <>
      {state.query.isLoading && <p role="status">Loading student choices…</p>}
      {state.error instanceof Error && (
        <div role="alert" className="academic-request-error">
          <p>Student choices: {state.error.message} Saved subjects are kept.</p>
          {state.query.isError && (
            <button type="button" className="academic-secondary-button" onClick={() => void state.query.refetch()}>
              Retry student choices
            </button>
          )}
        </div>
      )}
      {state.notice && <p role="status">{state.notice}</p>}
      {state.saving && <p role="status">Saving student choices…</p>}
    </>
  )
}

import type { usePrepareSemesters } from './usePrepareSemesters.ts'

export default function SemesterSetup({
  setup,
  hasDrafts,
}: {
  setup: ReturnType<typeof usePrepareSemesters>
  hasDrafts: boolean
}) {
  return (
    <section className="study-plan-guide" aria-label="Semester setup" aria-busy={setup.saving}>
      <h3>Set up semesters here</h3>
      <p>
        Semesters are shared by this program’s curricula and classes. Existing semesters keep their names, codes and
        links.
      </p>
      {setup.missing > 0 ? (
        <>
          <p>
            {setup.missing} {setup.missing === 1 ? 'semester needs' : 'semesters need'} setup. Create the missing
            semesters, then add their subjects below.
          </p>
          <button
            type="button"
            className="academic-primary-button"
            disabled={!setup.canPrepare || setup.saving}
            onClick={() => void setup.prepare()}
          >
            {setup.saving
              ? 'Setting up semesters…'
              : `Set up ${setup.missing} missing ${setup.missing === 1 ? 'semester' : 'semesters'}`}
          </button>
          {!setup.canPrepare && (
            <p>
              {hasDrafts
                ? 'Save or cancel open forms before setting up semesters.'
                : 'Semester setup requires permission to manage programs and an active draft curriculum.'}
            </p>
          )}
        </>
      ) : (
        <p>All semesters are set up. Use Semester settings on a card to change its name, code or active status.</p>
      )}
      {setup.saving && (
        <p role="status">
          Creating semester {Math.min(setup.progress.completed + 1, setup.progress.total)} of {setup.progress.total}.
          You can add subjects when setup finishes.
        </p>
      )}
      {setup.error && (
        <p role="alert" className="academic-request-error">
          {setup.error}
        </p>
      )}
      {setup.notice && <p role="status">{setup.notice}</p>}
    </section>
  )
}

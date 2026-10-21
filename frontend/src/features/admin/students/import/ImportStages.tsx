import { CheckCircle2, FileSpreadsheet, Info } from 'lucide-react'
import { ImportPagination } from './ImportPagination.tsx'
import { ImportPreviewTable } from './ImportPreviewTable.tsx'
import { ImportToolbar } from './ImportToolbar.tsx'
import type { StudentImportModel } from './useStudentImport.ts'
export function ImportStages({ model }: { model: StudentImportModel }) {
  const {
    directoryReady,
    registration,
    stage,
    busy,
    setFilter,
    setSearch,
    setPage,
    onlySelected,
    setOnlySelected,
    showFilters,
    outcomes,
    importProgress,
    reviewed,
    validSelected,
    importSelected,
  } = model
  return (
    <>
      {stage === 1 ? (
        <>
          <ImportToolbar model={model} />
          {showFilters && (
            <div id="student-import-filters" className="students-filter-panel">
              <label>
                <input
                  type="checkbox"
                  checked={onlySelected}
                  onChange={(event) => {
                    setOnlySelected(event.target.checked)
                    setPage(1)
                  }}
                />
                Show selected records only
              </label>
              <button
                className="students-text-button"
                onClick={() => {
                  setOnlySelected(false)
                  setFilter('all')
                  setSearch('')
                  setPage(1)
                }}
              >
                Clear filters
              </button>
            </div>
          )}
          <ImportPreviewTable model={model} />
          <ImportPagination model={model} />
        </>
      ) : stage === 3 ? (
        <section className="students-confirm" aria-label="Registration results">
          <div className="students-upload-icon">
            <CheckCircle2 />
          </div>
          <h2>Registration results</h2>
          <p role="status">
            Registered: {outcomes.filter((item) => item.status === 'imported').length} · Failed:{' '}
            {outcomes.filter((item) => item.status === 'failed').length} · Skipped: {reviewed.length - outcomes.length}
          </p>
          <div className="students-table-scroll">
            <table className="students-table">
              <caption className="sr-only">Bulk registration results</caption>
              <thead>
                <tr>
                  <th>File row</th>
                  <th>Student</th>
                  <th>Result</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {outcomes.map((item) => (
                  <tr key={item.row}>
                    <td>{item.row}</td>
                    <td className="student-name">{item.name}</td>
                    <td>
                      <span className={`students-status ${item.status === 'imported' ? 'valid' : 'invalid'}`}>
                        {item.status === 'imported' ? 'Registered' : 'Failed'}
                      </span>
                    </td>
                    <td className="validation-message">{item.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>Student accounts still require signup and approval before students can sign in.</p>
          {registration?.resultActions}
          {outcomes.some((item) => item.status === 'failed') && (
            <button
              className="students-button"
              disabled={
                busy ||
                registration?.resultsBusy ||
                !directoryReady ||
                !reviewed.some(
                  (row) =>
                    row.status === 'valid' && outcomes.some((item) => item.row === row.row && item.status === 'failed'),
                )
              }
              onClick={() =>
                void importSelected(
                  reviewed.filter(
                    (row) =>
                      row.status === 'valid' &&
                      outcomes.some((item) => item.row === row.row && item.status === 'failed'),
                  ),
                )
              }
            >
              {busy ? 'Registering students…' : 'Retry failed registrations'}
            </button>
          )}
        </section>
      ) : (
        <section className="students-confirm">
          <div className="students-upload-icon">
            <FileSpreadsheet />
          </div>
          <h2>{validSelected.length} records selected for import</h2>
          <p>
            Only selected records that passed file checks are included. Duplicates, invalid records, and conflicts are
            excluded.
          </p>
          <div className="students-alert">
            <Info />
            <span>
              {registration ? (
                'The selected students will be registered in this course, branch, section, and admission batch. Subjects can be assigned later. Account matching and permissions are checked again for each student.'
              ) : (
                <>
                  Saving bulk student records is not available yet. Download the validation report to keep your review.
                  No student records have been created or changed.
                </>
              )}
            </span>
          </div>
          <button
            className="students-button primary"
            disabled={!registration || busy || !directoryReady || !validSelected.length}
            onClick={() => void importSelected(validSelected)}
          >
            {registration
              ? busy
                ? `Registering students… ${importProgress.completed}/${importProgress.total}`
                : `Register ${validSelected.length} student${validSelected.length === 1 ? '' : 's'}`
              : 'Import unavailable'}
          </button>
        </section>
      )}
    </>
  )
}

import type { SubjectImportRow } from './subjectImportModel.ts'
import type { SubjectImportState } from './useSubjectImport.ts'

const TYPE_LABELS: Record<SubjectImportRow['course_type'], string> = {
  core: 'Core',
  elective: 'Elective',
  open_elective: 'Open elective',
  skill: 'Skill',
  project: 'Project',
}

function rowStatus(row: SubjectImportRow, state: SubjectImportState) {
  if (row.errors.length) return { tone: 'error', text: row.errors.join(' ') }
  const result = state.results.get(row.sourceRow)
  if (result?.status === 'done') return { tone: 'done', text: 'Imported' }
  if (result?.status === 'failed') return { tone: 'error', text: result.message ?? 'Could not save this row.' }
  return { tone: 'ready', text: row.existingCourseId ? 'Exists — will be reused' : 'Ready' }
}

export default function SubjectImportPreview({ state }: { state: SubjectImportState }) {
  const errors = state.rows.length - state.valid.length
  const reused = state.valid.filter((row) => row.existingCourseId).length
  return (
    <section className="subject-import-preview" aria-label="Import preview">
      <p className="subject-import-summary" role="status">
        <strong>{state.valid.length - reused}</strong> new · <strong>{reused}</strong> already exist ·{' '}
        <strong>{errors}</strong> with errors
        {state.done.length > 0 && (
          <>
            {' '}
            · <strong>{state.done.length}</strong> imported
          </>
        )}
      </p>
      {errors > 0 && (
        <p className="subject-import-hint">Rows with errors are skipped. Fix them in the file and choose it again.</p>
      )}
      <div className="subject-import-table" role="region" aria-label="Subject rows" tabIndex={0}>
        <table>
          <thead>
            <tr>
              <th scope="col">Row</th>
              <th scope="col">Subject</th>
              <th scope="col">Credits</th>
              {state.curriculumId && <th scope="col">Semester</th>}
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {state.rows.map((row) => {
              const status = rowStatus(row, state)
              return (
                <tr key={row.sourceRow}>
                  <td>{row.sourceRow}</td>
                  <td>
                    <strong>{row.code || '—'}</strong>
                    <small>{row.name || 'Missing name'}</small>
                  </td>
                  <td>{row.credits ?? '—'}</td>
                  {state.curriculumId && (
                    <td>
                      {row.semester ?? '—'}
                      {row.semester !== null && (
                        <small>
                          {TYPE_LABELS[row.course_type]}
                          {row.is_required ? ', compulsory' : ', choice'}
                        </small>
                      )}
                    </td>
                  )}
                  <td className={`subject-import-status is-${status.tone}`}>{status.text}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

import { AlertCircle, ChevronRight, Info } from 'lucide-react'
import { ImportFooter } from './import/ImportFooter.tsx'
import { ImportStages } from './import/ImportStages.tsx'
import { ImportUpload } from './import/ImportUpload.tsx'
import { type ReviewStatus } from './studentImport.ts'

import { statuses, steps, useStudentImport } from './import/useStudentImport.ts'
export type { StudentImportOutcome, StudentRegistrationImport } from './import/useStudentImport.ts'

export default function StudentImport(props: Parameters<typeof useStudentImport>[0]) {
  const model = useStudentImport(props)
  const {
    directoryReady,
    onBack,
    registration,
    embedded,
    upload,
    stage,
    busy,
    error,
    filter,
    setFilter,
    setPage,
    fileInput,
    counts,
    choose,
  } = model

  return (
    <section className="students-content" aria-label="Bulk student import">
      {!registration && !embedded && (
        <div className="students-breadcrumb">
          <button onClick={onBack}>Students</button>
          <ChevronRight />
          <span>Bulk Import</span>
          <ChevronRight />
          <span aria-current="page">
            {stage === 2 ? 'Confirm Import' : stage === 1 ? 'Validate & Preview' : 'Upload File'}
          </span>
        </div>
      )}
      {!registration && !embedded && (
        <div className="students-title">
          <div>
            <h1>Bulk Student Import</h1>
            <p>
              {stage === 2
                ? 'Review your selection before importing student records.'
                : 'Validate the uploaded file and review student records before importing.'}
            </p>
          </div>
        </div>
      )}
      <ol className="students-stepper" aria-label="Import progress">
        {steps.map(([label, description], index) => (
          <li
            key={label}
            className={index === stage ? 'is-current' : ''}
            aria-current={index === stage ? 'step' : undefined}
          >
            <span className="students-step-number">{index + 1}</span>
            <span>
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
          </li>
        ))}
      </ol>
      <input
        ref={fileInput}
        type="file"
        accept=".csv,.xlsx"
        aria-label="Choose student file"
        className="sr-only"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          if (file) void choose(file)
        }}
      />
      {error && (
        <div role="alert" className="students-alert error">
          <AlertCircle />
          <span>{error}</span>
        </div>
      )}
      <ImportUpload model={model} />
      {!upload && (
        <div className="students-format">
          <Info />
          <div>
            <strong>A little preparation goes a long way.</strong>
            <p>
              {registration
                ? 'Include name, register_number, and email. University roll number is optional. The selected course, branch, section, and batch apply to every row. Subjects and attendance are managed separately. '
                : 'Include name, register_number, university_roll_number, and email. Attendance is optional (0–100). '}
              Format identifiers as text to preserve leading zeros. Excel reads the first sheet.
            </p>
          </div>
        </div>
      )}
      {upload && (
        <>
          {stage !== 3 && (
            <div className="students-stats">
              {(Object.keys(statuses) as ReviewStatus[]).map((status) => {
                const { title, description, Icon } = statuses[status]
                return (
                  <button
                    key={status}
                    className={`students-stat ${status} ${filter === status ? 'is-selected' : ''}`}
                    onClick={() => {
                      setFilter(filter === status ? 'all' : status)
                      setPage(1)
                    }}
                    aria-pressed={filter === status}
                  >
                    <span className="students-stat-icon">
                      <Icon />
                    </span>
                    <span>
                      <strong>{counts[status]}</strong>
                      <b>{title}</b>
                      <small>{description}</small>
                    </span>
                  </button>
                )
              })}
            </div>
          )}
          {!directoryReady && (
            <div role="status" className="students-alert">
              <Info />
              <span>
                Student records must finish loading before existing student numbers can be checked. You can still review
                file errors.
              </span>
            </div>
          )}
          <ImportStages model={model} />
          <ImportFooter model={model} />
          <p className="students-review-note">
            {registration
              ? 'Validation checks this file against class registrations. Final identity and permission checks take place during registration.'
              : 'Validation checks this file and your institution’s student numbers. Final account and identity checks will be required before any import.'}
          </p>
        </>
      )}
    </section>
  )
}

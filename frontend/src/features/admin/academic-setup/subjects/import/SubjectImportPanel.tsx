import { Download, FileUp } from 'lucide-react'
import { SUBJECT_IMPORT_LIMIT, SUBJECT_TEMPLATE } from './subjectImportModel.ts'
import type { SubjectImportState } from './useSubjectImport.ts'
import SubjectImportPreview from './SubjectImportPreview.tsx'
import './subject-import.css'

function downloadTemplate() {
  const url = URL.createObjectURL(new Blob([SUBJECT_TEMPLATE], { type: 'text/csv' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: 'subjects-template.csv' })
  link.click()
  URL.revokeObjectURL(url)
}

/** File choice, format help, file errors and the row preview, shared by the dialog and Quick Setup. */
export default function SubjectImportPanel({ state }: { state: SubjectImportState }) {
  return (
    <>
      <div className="subject-import-file">
        <label className="academic-secondary-button">
          <FileUp aria-hidden="true" />
          <span>{state.fileName || 'Choose CSV file'}</span>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label="Subject CSV file"
            disabled={state.running}
            onChange={(event) => void state.chooseFile(event.target.files?.[0])}
          />
        </label>
        <button type="button" className="subject-import-template" onClick={downloadTemplate}>
          <Download aria-hidden="true" /> Download template
        </button>
      </div>
      <p className="subject-import-hint">
        Columns: code, name, credits, L, T, P, semester, type, required, description. Up to {SUBJECT_IMPORT_LIMIT} rows.
        Subjects whose code already exists in the department are reused, not duplicated.
      </p>
      {state.fileError && (
        <p className="subject-form-error" role="alert">
          {state.fileError}
        </p>
      )}
      {state.rows.length > 0 && <SubjectImportPreview state={state} />}
    </>
  )
}

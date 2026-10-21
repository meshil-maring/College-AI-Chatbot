import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { downloadCsv } from '../studentImport.ts'
import type { StudentImportModel } from './useStudentImport.ts'
export function ImportUpload({ model }: { model: StudentImportModel }) {
  const { registration, upload, busy, dragging, setDragging, fileInput, importing, reviewed, columns, choose } = model
  return (
    <>
      {upload ? (
        <div className="students-file">
          <div className="students-file-icon">
            <FileSpreadsheet />
          </div>
          <div className="students-file-details">
            <strong>{upload.name}</strong>
            <p>
              Uploaded on{' '}
              {new Intl.DateTimeFormat(undefined, {
                dateStyle: 'medium',
                timeStyle: 'short',
              }).format(upload.time)}
              <span>·</span>
              {reviewed.length.toLocaleString()} records detected
            </p>
          </div>
          <button
            className="students-button"
            disabled={busy || registration?.resultsBusy}
            onClick={() => fileInput.current?.click()}
          >
            <Upload />
            {busy && !importing.current ? 'Reading file…' : 'Replace File'}
          </button>
        </div>
      ) : (
        <div
          className={`students-dropzone ${dragging ? 'is-dragging' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            if (!busy && event.dataTransfer.files[0]) void choose(event.dataTransfer.files[0])
          }}
        >
          <div className="students-upload-icon">
            <Upload />
          </div>
          <h2>Bring your student records together</h2>
          <p>Drag and drop your spreadsheet here, or choose a file to get started.</p>
          <button className="students-button primary" disabled={busy} onClick={() => fileInput.current?.click()}>
            <Upload />
            {busy ? 'Reading file…' : 'Choose File'}
          </button>
          <small>Excel (.xlsx) or CSV · Up to 5 MB · 1,000 records</small>
          <button
            className="students-text-button"
            onClick={() => downloadCsv('student-import-template.csv', [columns])}
          >
            <Download />
            Download CSV template
          </button>
        </div>
      )}
    </>
  )
}

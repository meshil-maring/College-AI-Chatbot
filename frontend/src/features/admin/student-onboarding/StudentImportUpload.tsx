import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { useRef } from 'react'

function downloadTemplate() {
  const contents = 'Student Name,Register Number,University Roll No.,Email\r\n'
  const url = URL.createObjectURL(new Blob([contents], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'student-registration-template.csv'
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export default function StudentImportUpload({
  fileName,
  error,
  disabled,
  onFile,
}: {
  fileName: string
  error: string
  disabled: boolean
  onFile: (file?: File) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <div className="student-import-upload">
      <div className="student-import-upload-heading">
        <span className="student-import-upload-icon">
          <FileSpreadsheet size={22} />
        </span>
        <div>
          <h3>Upload your student list</h3>
          <p>Start with a CSV or Excel workbook. You can check and fix every row before sending.</p>
        </div>
        <button
          type="button"
          className="student-onboarding-secondary student-template-button"
          onClick={downloadTemplate}
        >
          <Download size={16} /> Download template
        </button>
      </div>
      <input
        ref={input}
        className="student-import-file-input"
        type="file"
        accept=".csv,.xlsx"
        aria-label="Choose student CSV or Excel file"
        disabled={disabled}
        onChange={(event) => {
          onFile(event.target.files?.[0])
          event.target.value = ''
        }}
      />
      <button
        type="button"
        className="student-import-dropzone"
        disabled={disabled}
        onClick={() => input.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          onFile(event.dataTransfer.files[0])
        }}
      >
        <span className="student-import-dropzone-icon">
          <Upload size={20} />
        </span>
        <strong>{fileName || 'Choose a file or drag it here'}</strong>
        <span>{fileName ? 'Choose a different file' : 'CSV or XLSX · up to 5 MB · maximum 500 students'}</span>
      </button>
      {error && (
        <p className="student-onboarding-inline-error" role="alert">
          {error}
        </p>
      )}
      <ul className="student-import-columns" aria-label="Required spreadsheet columns">
        <li>
          <b>Required</b> Student Name
        </li>
        <li>
          <b>Required</b> Register Number
        </li>
        <li>
          <b>Required</b> Email
        </li>
        <li>
          <b>Optional</b> University Roll No.
        </li>
      </ul>
    </div>
  )
}

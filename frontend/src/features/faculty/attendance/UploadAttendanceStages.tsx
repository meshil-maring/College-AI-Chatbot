import {
  AlertCircle,
  CheckCircle2,
  CloudUpload,
  FileImage,
  FileSpreadsheet,
  FileText,
  X,
} from 'lucide-react'
import type { FacultyAttendanceImportReview } from '../../../services/facultyAttendanceApi.ts'

const fieldDefinitions = [
  { label: 'Register Number', keys: ['register_number'], required: true },
  { label: 'Student Name', keys: ['student_name'], required: true },
  { label: 'University Roll Number', keys: ['university_roll_number', 'university_roll_no'], required: true },
  { label: 'Attendance', keys: ['attendance', 'attendance_status', 'attendance_percentage', 'status'], required: true },
  { label: 'Email', keys: ['email'], required: false },
  { label: 'Address', keys: ['address'], required: false },
]

export function UploadFileStage({
  dragging,
  pendingFile,
  aiConfirmationFile,
  saving,
  error,
  onDraggingChange,
  onFileSelected,
  onRemoveFile,
  onCancelAi,
  onProcess,
}: {
  dragging: boolean
  pendingFile: File | null
  aiConfirmationFile: File | null
  saving: boolean
  error: string | null
  onDraggingChange: (dragging: boolean) => void
  onFileSelected: (file: File | undefined) => void
  onRemoveFile: () => void
  onCancelAi: () => void
  onProcess: (file: File, aiConfirmed: boolean) => void
}) {
  return (
    <div className="pt-4">
      <div
        onDragOver={(event) => { event.preventDefault(); onDraggingChange(true) }}
        onDragLeave={() => onDraggingChange(false)}
        onDrop={(event) => {
          event.preventDefault()
          onDraggingChange(false)
          onFileSelected(event.dataTransfer.files[0])
        }}
        className={`rounded-lg border border-dashed px-5 py-7 text-center transition-colors ${dragging ? 'border-[#ffc72c] bg-[#ffc72c]/5' : 'border-[#3b5570] bg-[#0a1928]'}`}
      >
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-[#1b3148] text-[#d1def0]">
          <CloudUpload aria-hidden="true" size={25} strokeWidth={1.8} />
        </div>
        <h3 className="mt-3 text-sm font-semibold text-white">Upload Attendance File</h3>
        <p className="mt-1 text-xs text-slate-400">Drag and drop your file here, or</p>
        <label className="mt-3 inline-flex cursor-pointer items-center rounded-md bg-[#ffc72c] px-4 py-1.5 text-[11px] font-bold text-[#101820] hover:bg-[#ffd65d]">
          Choose File
          <input
            aria-label="Attendance file"
            type="file"
            accept=".csv,.xls,.xlsx,.pdf,.png,.jpg,.jpeg,.webp"
            className="sr-only"
            onChange={(event) => onFileSelected(event.target.files?.[0])}
          />
        </label>
        <p className="mt-3 text-[11px] font-semibold text-[#ffc72c]">Recommended: Excel (.xlsx) or CSV (.csv)</p>
        <p className="mt-1 text-[10px] text-slate-500">These files can be processed quickly without AI.</p>
        <div className="mt-3 flex justify-center gap-2" aria-label="Supported file types">
          <FileType icon={FileSpreadsheet} label="XLSX" tone="green" />
          <FileType icon={FileSpreadsheet} label="CSV" tone="green" />
          <FileType icon={FileText} label="PDF" tone="red" />
          <FileType icon={FileImage} label="JPG" tone="blue" />
          <FileType icon={FileImage} label="PNG" tone="blue" />
        </div>
      </div>

      <div className="mt-3 flex gap-2 rounded-md border border-blue-500/20 bg-blue-500/10 p-2.5 text-[10px] leading-4 text-blue-200">
        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white">
          <span className="text-[10px] font-bold">i</span>
        </span>
        <p>CSV and XLSX files are parsed deterministically. No AI processing is required. PDF and image files may require AI-assisted extraction and can consume tokens; confirmation is requested before processing.</p>
      </div>

      {pendingFile ? (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-md border border-[#2b435b] bg-[#102235] px-3 py-2 text-xs">
          <span className="truncate text-slate-200">{pendingFile.name}</span>
          <button type="button" onClick={onRemoveFile} aria-label="Remove selected file" className="text-slate-400 hover:text-white">
            <X aria-hidden="true" size={15} />
          </button>
        </div>
      ) : null}

      {aiConfirmationFile ? (
        <div role="alert" className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          <p className="font-semibold">AI Processing May Be Required</p>
          <p className="mt-1 text-[11px] text-amber-200/80">This file may require AI-assisted extraction. AI processing can consume tokens.</p>
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" className="rounded-md border border-[#2c455e] px-3 py-1.5" onClick={onCancelAi}>Cancel</button>
            <button type="button" disabled={saving} className="rounded-md bg-[#ffc72c] px-3 py-1.5 font-bold text-[#101820] disabled:opacity-50" onClick={() => onProcess(aiConfirmationFile, true)}>
              {saving ? 'Processing…' : 'Continue'}
            </button>
          </div>
        </div>
      ) : null}

      {error && error !== 'AI_CONFIRMATION_REQUIRED' ? <p role="alert" className="mt-3 text-xs text-red-300">{error}</p> : null}
      {pendingFile && !aiConfirmationFile ? (
        <div className="mt-3 flex justify-end gap-2 border-t border-[#1e3348] pt-3">
          <button type="button" onClick={onRemoveFile} className="rounded-md border border-[#2c455e] px-3 py-1.5 text-[11px] font-semibold text-slate-300">Cancel</button>
          <button type="button" disabled={saving} onClick={() => onProcess(pendingFile, false)} className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[11px] font-bold text-[#101820] disabled:opacity-50">
            {saving ? 'Working…' : 'Process File'}
          </button>
        </div>
      ) : null}
    </div>
  )
}

export function ValidationResultsStage({
  review,
  onBack,
  onContinue,
  onDownloadErrors,
}: {
  review: FacultyAttendanceImportReview | null
  onBack: () => void
  onContinue: () => void
  onDownloadErrors: () => void
}) {
  const summary = review?.summary ?? {}
  const count = (...keys: string[]) => {
    for (const key of keys) {
      const value = summary[key]
      if (typeof value === 'number' && Number.isFinite(value)) return value
    }
    return 0
  }
  const valid = typeof summary.valid === 'number'
    ? summary.valid
    : typeof summary.VALID === 'number'
      ? summary.VALID
      : count('new_records', 'NEW') + count('updates', 'UPDATE')
  const errors = count('errors', 'ERROR') + count('conflicts', 'CONFLICT')
  const duplicateCount = count('duplicates', 'DUPLICATE')
  const rows = review?.rows ?? []
  const hasErrorRows = rows.some((row) => row.errors.length > 0)

  return (
    <div className="pt-4">
      <div className="flex items-center gap-2 rounded-md border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
        <CheckCircle2 aria-hidden="true" size={16} className="shrink-0 text-emerald-400" />
        <div><p className="font-semibold">File processed successfully</p><p className="text-[10px] text-emerald-300/80">{review?.summary.total_rows ?? rows.length} rows detected</p></div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <ValidationCount label="Valid Records" value={valid} tone="green" />
        <ValidationCount label="New Records" value={count('new_records', 'NEW')} tone="blue" />
        <ValidationCount label="Updates" value={count('updates', 'UPDATE')} tone="amber" />
        <ValidationCount label="Errors" value={errors} tone="red" />
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <h3 className="text-xs font-semibold text-white">Required Fields</h3>
        <span className="text-[10px] text-slate-500">Validation summary</span>
      </div>
      <div className="mt-1 overflow-hidden rounded-md border border-[#1e3348]">
        <table className="w-full text-left text-[10px]">
          <thead className="bg-[#0a1725] text-slate-500"><tr><th className="px-2 py-1.5 font-medium">Field</th><th className="px-2 py-1.5 font-medium">Status</th></tr></thead>
          <tbody>
            {fieldDefinitions.map((field) => {
              const present = rows.filter((row) => field.keys.some((key) => {
                const value = row.normalized_data[key]
                return value !== undefined && value.trim().length > 0
              })).length
              const missing = Math.max(0, rows.length - present)
              const complete = missing === 0
              const status = rows.length === 0
                ? 'No data'
                : field.required
                  ? complete ? `${present} / ${rows.length} present` : `${missing} missing`
                  : `${present} / ${rows.length} provided`
              return (
                <tr key={field.label} className="border-t border-[#1b3044]">
                  <td className="px-2 py-1 text-slate-300">{field.label}{!field.required ? <span className="ml-1 text-slate-500">(optional)</span> : null}</td>
                  <td className="px-2 py-1">
                    <span className={`inline-flex items-center gap-1 ${rows.length === 0 ? 'text-slate-500' : complete || !field.required ? 'text-emerald-300' : 'text-amber-300'}`}>
                      {rows.length > 0 && complete ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
                      {status}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex flex-col-reverse gap-2 border-t border-[#1e3348] pt-3 sm:flex-row sm:justify-between">
        <button type="button" onClick={onDownloadErrors} disabled={!hasErrorRows} className="inline-flex items-center justify-center gap-1.5 rounded-md border border-[#304862] px-3 py-1.5 text-[10px] font-semibold text-slate-300 hover:bg-[#142638] disabled:opacity-50">
          Download Error Report
        </button>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onBack} className="rounded-md border border-[#304862] px-3 py-1.5 text-[10px] font-semibold text-slate-300">Back</button>
          <button type="button" onClick={onContinue} className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[10px] font-bold text-[#101820]">Continue to Review</button>
        </div>
      </div>
      {duplicateCount > 0 ? <p className="mt-2 text-[10px] text-slate-500">{duplicateCount} duplicate records were detected.</p> : null}
    </div>
  )
}

export function ReviewImportStage({
  review,
  saving,
  onBack,
  onCommit,
  error,
  onCorrect,
  readOnly = false,
}: {
  review: FacultyAttendanceImportReview | null
  saving: boolean
  onBack: () => void
  onCommit: () => void
  error: string | null
  onCorrect?: (row: number, data: Record<string, string>) => void
  readOnly?: boolean
}) {
  const summary = review?.summary ?? {}
  const errors = Number(summary.errors ?? summary.ERROR ?? 0) + Number(summary.conflicts ?? summary.CONFLICT ?? 0) + Number(summary.duplicates ?? summary.DUPLICATE ?? 0)
  const valid = Number(summary.valid ?? Number(summary.new_records ?? summary.NEW ?? 0) + Number(summary.updates ?? summary.UPDATE ?? 0))

  return (
    <div className="pt-4">
      <div className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
        <span className="font-semibold">File processed successfully</span>
        <span className="ml-2 text-[10px] text-emerald-300/80">{summary.total_rows ?? review?.rows.length ?? 0} records detected</span>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-white">Review Import</h3>
        <span className="text-[10px] text-slate-400">{valid} valid · {errors} errors</span>
      </div>
      {errors > 0 ? <div className="mt-2 flex gap-2 rounded-md border border-red-500/20 bg-red-500/10 p-2.5 text-[10px] text-red-200"><AlertCircle aria-hidden="true" size={14} className="shrink-0" /><span><strong>{errors} records have errors</strong> and cannot be imported.</span></div> : null}
      <div className="mt-2 max-h-56 overflow-auto rounded-md border border-[#1e3348]">
        <table className="min-w-full text-left text-[10px]">
          <thead className="bg-[#0a1725] text-slate-500"><tr><th className="p-2">Row</th><th className="p-2">Register No.</th><th className="p-2">Student Name</th><th className="p-2">Issue</th></tr></thead>
          <tbody>{review?.rows.map((row) => (
            <tr key={row.row_number} className="border-t border-[#1e3348] text-slate-300">
              <td className="p-2">{row.row_number}</td>
              <td className="p-2">{row.normalized_data.register_number ?? '—'}</td>
              <td className="p-2">{row.normalized_data.student_name ?? '—'}</td>
              <td className={`p-2 ${row.errors.length > 0 ? 'text-red-200' : 'text-emerald-300'}`}><span>{row.validation_status === 'CONFLICT' ? 'CONFLICT' : row.errors.length ? 'ERROR' : row.warnings?.length ? 'WARNING' : 'VALID'}</span> · {row.errors.join('; ') || row.warnings?.join('; ') || 'Ready to import'}<details><summary className="cursor-pointer py-1 text-slate-300">{readOnly ? 'Values' : 'Values / correction'}</summary><form onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>; onCorrect?.(row.row_number, data) }} className="grid gap-1">{Array.from(new Set([...Object.keys(row.normalized_data), 'register_number', 'university_roll_number', 'student_name', 'status', 'session_date', 'attendance_percentage'])).map((key) => <label key={key}>{key}<input name={key} readOnly={readOnly} aria-label={`${key} row ${row.row_number}`} defaultValue={row.normalized_data[key] ?? ''} className="ml-1 rounded border border-slate-600 bg-slate-900 p-1 text-white" /></label>)}{onCorrect && row.row_number >= 2 ? <button disabled={saving} type="submit" className="p-1 text-yellow-300">Save correction and validate again</button> : null}</form></details></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      {error && error !== 'AI_CONFIRMATION_REQUIRED' ? <p role="alert" className="mt-3 text-xs text-red-300">{error}</p> : null}
      <div className="mt-3 flex justify-end gap-2 border-t border-[#1e3348] pt-3">
        <button type="button" onClick={onBack} className="rounded-md border border-[#2c455e] px-3 py-1.5 text-[10px] font-semibold text-slate-300 hover:bg-[#142638]">Back to Validate</button>
        <button type="button" disabled={saving || readOnly || valid === 0 || errors > 0 || Boolean(review?.rows.some((row) => row.errors.length > 0))} onClick={onCommit} className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[10px] font-bold text-[#101820] disabled:opacity-50">
          {readOnly ? review?.status === 'IMPORTED' ? 'Already Imported' : 'Monitoring only' : saving ? 'Importing…' : `Import ${valid} Valid Records`}
        </button>
      </div>
    </div>
  )
}

function FileType({ icon: Icon, label, tone }: { icon: typeof FileText; label: string; tone: 'green' | 'red' | 'blue' }) {
  const tones = {
    green: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    red: 'border-red-500/30 bg-red-500/10 text-red-300',
    blue: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  }
  return <span className={`inline-flex h-7 min-w-8 flex-col items-center justify-center rounded border px-1 ${tones[tone]}`}><Icon aria-hidden="true" size={12} /><span className="text-[7px] font-bold">{label}</span></span>
}

function ValidationCount({ label, value, tone }: { label: string; value: number; tone: 'green' | 'blue' | 'amber' | 'red' }) {
  const colors = {
    green: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    blue: 'border-blue-500/20 bg-blue-500/10 text-blue-300',
    amber: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
    red: 'border-red-500/20 bg-red-500/10 text-red-300',
  }
  return <div className={`rounded-md border p-2 ${colors[tone]}`}><p className="text-base font-bold leading-5">{value}</p><p className="mt-0.5 text-[9px] text-slate-400">{label}</p></div>
}

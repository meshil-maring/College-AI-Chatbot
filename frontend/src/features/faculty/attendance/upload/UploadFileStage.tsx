import { CloudUpload, FileImage, FileSpreadsheet, FileText, X } from 'lucide-react'
export const fieldDefinitions = [
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
        onDragOver={(event) => {
          event.preventDefault()
          onDraggingChange(true)
        }}
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
        <p>
          CSV and XLSX files are parsed deterministically. No AI processing is required. PDF and image files may require
          AI-assisted extraction and can consume tokens; confirmation is requested before processing.
        </p>
      </div>

      {pendingFile ? (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-md border border-[#2b435b] bg-[#102235] px-3 py-2 text-xs">
          <span className="truncate text-slate-200">{pendingFile.name}</span>
          <button
            type="button"
            onClick={onRemoveFile}
            aria-label="Remove selected file"
            className="text-slate-400 hover:text-white"
          >
            <X aria-hidden="true" size={15} />
          </button>
        </div>
      ) : null}

      {aiConfirmationFile ? (
        <div
          role="alert"
          className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100"
        >
          <p className="font-semibold">AI Processing May Be Required</p>
          <p className="mt-1 text-[11px] text-amber-200/80">
            This file may require AI-assisted extraction. AI processing can consume tokens.
          </p>
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" className="rounded-md border border-[#2c455e] px-3 py-1.5" onClick={onCancelAi}>
              Cancel
            </button>
            <button
              type="button"
              disabled={saving}
              className="rounded-md bg-[#ffc72c] px-3 py-1.5 font-bold text-[#101820] disabled:opacity-50"
              onClick={() => onProcess(aiConfirmationFile, true)}
            >
              {saving ? 'Processing…' : 'Continue'}
            </button>
          </div>
        </div>
      ) : null}

      {error && error !== 'AI_CONFIRMATION_REQUIRED' ? (
        <p role="alert" className="mt-3 text-xs text-red-300">
          {error}
        </p>
      ) : null}
      {pendingFile && !aiConfirmationFile ? (
        <div className="mt-3 flex justify-end gap-2 border-t border-[#1e3348] pt-3">
          <button
            type="button"
            onClick={onRemoveFile}
            className="rounded-md border border-[#2c455e] px-3 py-1.5 text-[11px] font-semibold text-slate-300"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={() => onProcess(pendingFile, false)}
            className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[11px] font-bold text-[#101820] disabled:opacity-50"
          >
            {saving ? 'Working…' : 'Process File'}
          </button>
        </div>
      ) : null}
    </div>
  )
}

export function FileType({
  icon: Icon,
  label,
  tone,
}: {
  icon: typeof FileText
  label: string
  tone: 'green' | 'red' | 'blue'
}) {
  const tones = {
    green: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    red: 'border-red-500/30 bg-red-500/10 text-red-300',
    blue: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
  }
  return (
    <span className={`inline-flex h-7 min-w-8 flex-col items-center justify-center rounded border px-1 ${tones[tone]}`}>
      <Icon aria-hidden="true" size={12} />
      <span className="text-[7px] font-bold">{label}</span>
    </span>
  )
}

import { AlertCircle, CheckCircle2 } from 'lucide-react'
import type { FacultyAttendanceImportReview } from '../../../../services/faculty/facultyAttendanceApi.ts'
import { fieldDefinitions } from './UploadFileStage.tsx'
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
  const valid =
    typeof summary.valid === 'number'
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
        <div>
          <p className="font-semibold">File processed successfully</p>
          <p className="text-[10px] text-emerald-300/80">{review?.summary.total_rows ?? rows.length} rows detected</p>
        </div>
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
          <thead className="bg-[#0a1725] text-slate-500">
            <tr>
              <th className="px-2 py-1.5 font-medium">Field</th>
              <th className="px-2 py-1.5 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {fieldDefinitions.map((field) => {
              const present = rows.filter((row) =>
                field.keys.some((key) => {
                  const value = row.normalized_data[key]
                  return value !== undefined && value.trim().length > 0
                }),
              ).length
              const missing = Math.max(0, rows.length - present)
              const complete = missing === 0
              const status =
                rows.length === 0
                  ? 'No data'
                  : field.required
                    ? complete
                      ? `${present} / ${rows.length} present`
                      : `${missing} missing`
                    : `${present} / ${rows.length} provided`
              return (
                <tr key={field.label} className="border-t border-[#1b3044]">
                  <td className="px-2 py-1 text-slate-300">
                    {field.label}
                    {!field.required ? <span className="ml-1 text-slate-500">(optional)</span> : null}
                  </td>
                  <td className="px-2 py-1">
                    <span
                      className={`inline-flex items-center gap-1 ${rows.length === 0 ? 'text-slate-500' : complete || !field.required ? 'text-emerald-300' : 'text-amber-300'}`}
                    >
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
        <button
          type="button"
          onClick={onDownloadErrors}
          disabled={!hasErrorRows}
          className="inline-flex items-center justify-center gap-1.5 rounded-md border border-[#304862] px-3 py-1.5 text-[10px] font-semibold text-slate-300 hover:bg-[#142638] disabled:opacity-50"
        >
          Download Error Report
        </button>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onBack}
            className="rounded-md border border-[#304862] px-3 py-1.5 text-[10px] font-semibold text-slate-300"
          >
            Back
          </button>
          <button
            type="button"
            onClick={onContinue}
            className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[10px] font-bold text-[#101820]"
          >
            Continue to Review
          </button>
        </div>
      </div>
      {duplicateCount > 0 ? (
        <p className="mt-2 text-[10px] text-slate-500">{duplicateCount} duplicate records were detected.</p>
      ) : null}
    </div>
  )
}

export function ValidationCount({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'green' | 'blue' | 'amber' | 'red'
}) {
  const colors = {
    green: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    blue: 'border-blue-500/20 bg-blue-500/10 text-blue-300',
    amber: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
    red: 'border-red-500/20 bg-red-500/10 text-red-300',
  }
  return (
    <div className={`rounded-md border p-2 ${colors[tone]}`}>
      <p className="text-base font-bold leading-5">{value}</p>
      <p className="mt-0.5 text-[9px] text-slate-400">{label}</p>
    </div>
  )
}

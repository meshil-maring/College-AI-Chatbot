import { AlertCircle } from 'lucide-react'
import type { FacultyAttendanceImportReview } from '../../../../services/faculty/facultyAttendanceApi.ts'

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
  const errors =
    Number(summary.errors ?? summary.ERROR ?? 0) +
    Number(summary.conflicts ?? summary.CONFLICT ?? 0) +
    Number(summary.duplicates ?? summary.DUPLICATE ?? 0)
  const valid = Number(
    summary.valid ?? Number(summary.new_records ?? summary.NEW ?? 0) + Number(summary.updates ?? summary.UPDATE ?? 0),
  )

  return (
    <div className="pt-4">
      <div className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
        <span className="font-semibold">File processed successfully</span>
        <span className="ml-2 text-[10px] text-emerald-300/80">
          {summary.total_rows ?? review?.rows.length ?? 0} records detected
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-white">Review Import</h3>
        <span className="text-[10px] text-slate-400">
          {valid} valid · {errors} errors
        </span>
      </div>
      {errors > 0 ? (
        <div className="mt-2 flex gap-2 rounded-md border border-red-500/20 bg-red-500/10 p-2.5 text-[10px] text-red-200">
          <AlertCircle aria-hidden="true" size={14} className="shrink-0" />
          <span>
            <strong>{errors} records have errors</strong> and cannot be imported.
          </span>
        </div>
      ) : null}
      <div className="mt-2 max-h-56 overflow-auto rounded-md border border-[#1e3348]">
        <table className="min-w-full text-left text-[10px]">
          <thead className="bg-[#0a1725] text-slate-500">
            <tr>
              <th className="p-2">Row</th>
              <th className="p-2">Register No.</th>
              <th className="p-2">Student Name</th>
              <th className="p-2">Issue</th>
            </tr>
          </thead>
          <tbody>
            {review?.rows.map((row) => (
              <tr key={row.row_number} className="border-t border-[#1e3348] text-slate-300">
                <td className="p-2">{row.row_number}</td>
                <td className="p-2">{row.normalized_data.register_number ?? '—'}</td>
                <td className="p-2">{row.normalized_data.student_name ?? '—'}</td>
                <td className={`p-2 ${row.errors.length > 0 ? 'text-red-200' : 'text-emerald-300'}`}>
                  <span>
                    {row.validation_status === 'CONFLICT'
                      ? 'CONFLICT'
                      : row.errors.length
                        ? 'ERROR'
                        : row.warnings?.length
                          ? 'WARNING'
                          : 'VALID'}
                  </span>{' '}
                  · {row.errors.join('; ') || row.warnings?.join('; ') || 'Ready to import'}
                  <details>
                    <summary className="cursor-pointer py-1 text-slate-300">
                      {readOnly ? 'Values' : 'Values / correction'}
                    </summary>
                    <form
                      onSubmit={(event) => {
                        event.preventDefault()
                        const data = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<
                          string,
                          string
                        >
                        onCorrect?.(row.row_number, data)
                      }}
                      className="grid gap-1"
                    >
                      {Array.from(
                        new Set([
                          ...Object.keys(row.normalized_data),
                          'register_number',
                          'university_roll_number',
                          'student_name',
                          'status',
                          'session_date',
                          'attendance_percentage',
                        ]),
                      ).map((key) => (
                        <label key={key}>
                          {key}
                          <input
                            name={key}
                            readOnly={readOnly}
                            aria-label={`${key} row ${row.row_number}`}
                            defaultValue={row.normalized_data[key] ?? ''}
                            className="ml-1 rounded border border-slate-600 bg-slate-900 p-1 text-white"
                          />
                        </label>
                      ))}
                      {onCorrect && row.row_number >= 2 ? (
                        <button disabled={saving} type="submit" className="p-1 text-yellow-300">
                          Save correction and validate again
                        </button>
                      ) : null}
                    </form>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && error !== 'AI_CONFIRMATION_REQUIRED' ? (
        <p role="alert" className="mt-3 text-xs text-red-300">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex justify-end gap-2 border-t border-[#1e3348] pt-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-md border border-[#2c455e] px-3 py-1.5 text-[10px] font-semibold text-slate-300 hover:bg-[#142638]"
        >
          Back to Validate
        </button>
        <button
          type="button"
          disabled={
            saving ||
            readOnly ||
            valid === 0 ||
            errors > 0 ||
            Boolean(review?.rows.some((row) => row.errors.length > 0))
          }
          onClick={onCommit}
          className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[10px] font-bold text-[#101820] disabled:opacity-50"
        >
          {readOnly
            ? review?.status === 'IMPORTED'
              ? 'Already Imported'
              : 'Monitoring only'
            : saving
              ? 'Importing…'
              : `Import ${valid} Valid Records`}
        </button>
      </div>
    </div>
  )
}

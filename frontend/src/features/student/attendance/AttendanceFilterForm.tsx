/**
 * Server-side date-range filter form. Values are sent to the backend as
 * `date_from` / `date_to`; the SERVER validates them (422 INVALID_FILTER) and
 * remains authoritative — the UI never narrows data locally. Date-range
 * filtering is not security-sensitive: the endpoint always scopes rows to the
 * authenticated student's own records first.
 */
export function AttendanceFilterForm({
  fromDraft,
  toDraft,
  onFromChange,
  onToChange,
  onApply,
  onReset,
}: {
  fromDraft: string
  toDraft: string
  onFromChange: (value: string) => void
  onToChange: (value: string) => void
  onApply: () => void
  onReset: () => void
}) {
  return (
    <form
      className="mt-4 rounded-lg border border-slate-700 bg-slate-900/40 p-3"
      aria-label="Attendance date filter"
      onSubmit={(event) => {
        event.preventDefault()
        onApply()
      }}
    >
      <p className="text-xs text-slate-400">
        Narrow your own attendance by date. The server applies this filter to your records.
      </p>
      <div className="mt-2 flex flex-wrap items-end gap-3">
        <div className="min-w-[9rem]">
          <label htmlFor="attendance-filter-from" className="block text-xs font-medium text-slate-300">
            From date
          </label>
          <input
            id="attendance-filter-from"
            type="date"
            value={fromDraft}
            onChange={(event) => onFromChange(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
        </div>
        <div className="min-w-[9rem]">
          <label htmlFor="attendance-filter-to" className="block text-xs font-medium text-slate-300">
            To date
          </label>
          <input
            id="attendance-filter-to"
            type="date"
            value={toDraft}
            onChange={(event) => onToChange(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Apply date filter
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Reset filter
        </button>
      </div>
    </form>
  )
}

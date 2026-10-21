import { useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import type { FacultyAttendanceAssignment, FacultyStudentRegistrationEvent } from '../../../services/faculty/facultyAttendanceApi.ts'
import { useStudentWorkspaceApi } from '../../students/StudentWorkspaceContext.tsx'

const input = 'mt-1 w-full rounded-lg border border-[#304862] bg-[#091725] px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#ffc72c]'
const button = 'rounded-lg border border-[#304862] px-3 py-2 text-sm text-slate-200 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
const PAGE_SIZE = 25
const ACTIONS: Record<FacultyStudentRegistrationEvent['action'], string> = {
  roster_added: 'Added to roster', roster_imported: 'Imported to roster', roster_updated: 'Student record updated',
  roster_removed: 'Removed from roster', account_updated: 'Account status updated', account_approved: 'Account approved',
  account_pending: 'Account awaiting approval', identity_conflict: 'Identity review required',
  class_registered: 'Registered in class; subjects assigned separately',
}

export default function FacultyStudentRecordHistory({ token, assignment }: { token: string; assignment: FacultyAttendanceAssignment }) {
  const api = useStudentWorkspaceApi()
  const [filters, setFilters] = useState({ search: '', page: 0 })
  const [draftSearch, setDraftSearch] = useState('')
  const history = useApiQuery(
    [api.namespace, 'students', token, assignment.section_id, 'registration-history', filters],
    () => api.getHistory(token, assignment.section_id, new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(filters.page * PAGE_SIZE), search: filters.search })),
  )
  const result = history.isError ? undefined : history.data
  return <section aria-label="Student registration history" className="space-y-4 rounded-xl border border-[#26394e] bg-[#0d1c2c] p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="text-lg font-semibold text-white">Record history</h2><p className="mt-1 text-sm text-slate-400">Student registration activity for {assignment.section.name}: roster additions, record changes, and account status updates.</p></div>
      <button type="button" className={`${button} inline-flex items-center gap-2`} disabled={history.isFetching} onClick={() => { void history.refetch() }}><RefreshCw aria-hidden="true" size={16} />Refresh history</button>
    </div>
    <form className="flex flex-wrap items-end gap-2" onSubmit={(event) => { event.preventDefault(); setFilters({ search: draftSearch.trim(), page: 0 }) }}>
      <label className="min-w-0 flex-1 text-xs text-slate-400">Search registration history<input className={input} maxLength={128} placeholder="Student name, register number or roll number" value={draftSearch} onChange={(event) => setDraftSearch(event.target.value)} /></label>
      <button type="submit" className={`${button} inline-flex items-center gap-2`}><Search aria-hidden="true" size={16} />Search history</button>
      {filters.search ? <button type="button" className={button} onClick={() => { setDraftSearch(''); setFilters({ search: '', page: 0 }) }}>Clear search</button> : null}
    </form>
    {history.isError ? <div role="alert" className="space-y-3 text-sm text-red-300"><p>{history.error instanceof Error ? history.error.message : 'Registration history could not be loaded.'}</p><button type="button" className={button} onClick={() => { void history.refetch() }}>Try again</button></div>
      : history.isPending ? <p role="status" className="py-10 text-center text-sm text-slate-400">Loading registration history…</p>
        : result?.items.length ? <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm">
          <caption className="sr-only">Student registration activity in {assignment.section.name}</caption>
          <thead className="border-b border-[#304862] text-xs text-slate-400"><tr>{['Date and time', 'Student', 'Register number', 'University roll number', 'Activity'].map((label) => <th key={label} scope="col" className="px-3 py-3">{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-[#26394e]">{result.items.map((event) => <tr key={event.event_id} className="text-slate-300 hover:bg-[#142638]">
            <td className="whitespace-nowrap px-3 py-4">{event.occurred_at ? <time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time> : 'Not recorded'}</td>
            <td className="px-3 py-4 font-medium text-white">{event.student_name}</td><td className="px-3 py-4">{event.register_number ?? 'Not recorded'}</td><td className="px-3 py-4">{event.university_roll_number ?? 'Not recorded'}</td><td className="px-3 py-4">{ACTIONS[event.action]}</td>
          </tr>)}</tbody>
        </table></div> : <p role="status" className="py-10 text-center text-sm text-slate-400">{filters.search ? 'No registration activity matches your search.' : 'No registration activity recorded for this section yet.'}</p>}
    {result ? <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#26394e] pt-4">
      <p role="status" className="text-xs text-slate-400">{result.total === 0 ? '0 records' : !result.items.length ? `0 of ${result.total} records on this page` : `${filters.page * PAGE_SIZE + 1}–${filters.page * PAGE_SIZE + result.items.length} of ${result.total} records`}</p>
      <div className="flex gap-2"><button type="button" className={button} disabled={filters.page === 0 || history.isFetching} onClick={() => setFilters((current) => ({ ...current, page: current.page - 1 }))}>Previous history page</button><button type="button" className={button} disabled={(filters.page + 1) * PAGE_SIZE >= result.total || history.isFetching} onClick={() => setFilters((current) => ({ ...current, page: current.page + 1 }))}>Next history page</button></div>
    </div> : null}
  </section>
}

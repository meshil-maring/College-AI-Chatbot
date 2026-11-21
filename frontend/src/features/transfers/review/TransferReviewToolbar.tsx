import { Search, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { TRANSFER_STATUS_LABEL } from '../transferLabels.ts'
import { TAB_STATUSES, hasActiveFilters, type ReviewTab, type TransferFilters } from './transferFilters.ts'

const CONTROL = 'min-h-10 w-full rounded-lg border border-control bg-surface px-3 text-content'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-muted">
      {label}
      {children}
    </label>
  )
}

export default function TransferReviewToolbar({
  tab,
  filters,
  programs,
  departments,
  showDepartments,
  resultCount,
  onChange,
  onClear,
}: {
  tab: ReviewTab
  filters: TransferFilters
  programs: { id: string; name: string }[]
  departments: { id: string; name: string }[]
  showDepartments: boolean
  resultCount: number
  onChange: (next: Partial<TransferFilters>) => void
  onClear: () => void
}) {
  return (
    <div className="ui-panel space-y-3 p-4" role="search" aria-label="Search and filter transfer requests">
      <div className="relative">
        <Search size={16} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="search"
          value={filters.search}
          onChange={(event) => onChange({ search: event.target.value })}
          placeholder="Search by student, register number, program, section or reason"
          aria-label="Search transfer requests"
          className={`${CONTROL} pl-9`}
        />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Status">
          <select
            className={CONTROL}
            value={filters.status}
            onChange={(event) => onChange({ status: event.target.value as TransferFilters['status'] })}
          >
            <option value="all">{tab === 'pending' ? 'All pending' : 'All outcomes'}</option>
            {TAB_STATUSES[tab].map((status) => (
              <option key={status} value={status}>
                {TRANSFER_STATUS_LABEL[status]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Transfer type">
          <select
            className={CONTROL}
            value={filters.type}
            onChange={(event) => onChange({ type: event.target.value as TransferFilters['type'] })}
          >
            <option value="all">All types</option>
            <option value="section_transfer">Section transfer</option>
            <option value="program_transfer">Program transfer</option>
          </select>
        </Field>
        <Field label="Started by">
          <select
            className={CONTROL}
            value={filters.initiatedBy}
            onChange={(event) => onChange({ initiatedBy: event.target.value as TransferFilters['initiatedBy'] })}
          >
            <option value="all">Anyone</option>
            <option value="student">Student request</option>
            <option value="admin">Administrator</option>
            <option value="hod">Head of Department</option>
          </select>
        </Field>
        <Field label="Program">
          <select
            className={CONTROL}
            value={filters.programId}
            onChange={(event) => onChange({ programId: event.target.value })}
          >
            <option value="">All programs</option>
            {programs.map((program) => (
              <option key={program.id} value={program.id}>
                {program.name}
              </option>
            ))}
          </select>
        </Field>
        {showDepartments && (
          <Field label="Department">
            <select
              className={CONTROL}
              value={filters.departmentId}
              onChange={(event) => onChange({ departmentId: event.target.value })}
            >
              <option value="">All departments</option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Period">
          <select
            className={CONTROL}
            value={filters.period}
            onChange={(event) => onChange({ period: event.target.value as TransferFilters['period'] })}
          >
            <option value="any">Any time</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
        </Field>
        <Field label="Sort">
          <select
            className={CONTROL}
            value={filters.sort}
            onChange={(event) => onChange({ sort: event.target.value as TransferFilters['sort'] })}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </Field>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <p className="text-muted" aria-live="polite">
          {resultCount} {resultCount === 1 ? 'request' : 'requests'}
        </p>
        {hasActiveFilters(filters) && (
          <button
            type="button"
            onClick={onClear}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-content hover:bg-hover"
          >
            <X size={16} aria-hidden="true" /> Clear filters
          </button>
        )}
      </div>
    </div>
  )
}

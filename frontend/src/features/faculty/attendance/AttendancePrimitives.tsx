import {
  AlertTriangle,
  CalendarDays,
  Clock3,
  Users,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import type { FacultyAttendanceRosterRow } from '../../../services/facultyAttendanceApi.ts'

type MetricIcon = 'users' | 'calendar' | 'clock' | 'alert'
type MetricTone = 'yellow' | 'cyan' | 'green' | 'blue' | 'red' | 'amber'

const metricIcons: Record<MetricIcon, LucideIcon> = {
  users: Users,
  calendar: CalendarDays,
  clock: Clock3,
  alert: AlertTriangle,
}

const metricTones: Record<MetricTone, string> = {
  yellow: 'bg-[#332a12] text-[#ffc72c]',
  cyan: 'bg-[#073640] text-[#20d5d2]',
  green: 'bg-[#063c34] text-[#23d29e]',
  blue: 'bg-[#102f59] text-[#4ca2ff]',
  red: 'bg-[#401c2a] text-[#fb5a6b]',
  amber: 'bg-[#3b2e13] text-[#ffc72c]',
}

export function AttendanceScopeSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange?: (value: string) => void
}) {
  return (
    <label className="block min-w-0 text-[11px] text-slate-400">
      {label}
      <select
        aria-label={label}
        className="mt-1 h-[29px] w-full rounded-md border border-[#263d55] bg-[#091725] px-2 text-xs text-slate-100 outline-none focus:border-[#ffc72c] focus:ring-1 focus:ring-[#ffc72c]"
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
      >
        {options.map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  )
}

export function AttendanceMetric({
  label,
  value,
  icon,
  tone,
}: {
  label: ReactNode
  value: number | string | null
  icon: MetricIcon
  tone: MetricTone
}) {
  const Icon = metricIcons[icon]
  return (
    <div className="flex min-h-[64px] min-w-0 items-center gap-3 rounded-lg border border-[#1e3348] bg-[linear-gradient(135deg,#0d1c2c_0%,#0b1826_100%)] px-3 py-2 shadow-[0_8px_18px_rgba(2,8,23,0.12)]">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${metricTones[tone]}`}>
        <Icon aria-hidden="true" size={21} strokeWidth={1.8} />
      </div>
      <div className="min-w-0">
        <p className="text-lg font-bold leading-5 text-white">{value === null ? '—' : value}</p>
        <p className="mt-0.5 text-[11px] leading-4 text-slate-300">{label}</p>
      </div>
    </div>
  )
}

export function AttendanceStatusBadge({
  row,
  percentage,
}: {
  row: FacultyAttendanceRosterRow
  percentage: number | null
}) {
  const low = percentage !== null && percentage < 75
  const label = {
    ACTIVE: 'Active',
    UNREGISTERED: 'Unregistered',
    PENDING_APPROVAL: 'Pending Approval',
    INACTIVE: 'Inactive',
  }[row.roster_status]
  const tone = row.roster_status === 'INACTIVE'
    ? 'bg-red-500/10 text-red-300'
    : row.roster_status === 'ACTIVE'
      ? 'bg-emerald-500/10 text-emerald-300'
      : 'bg-amber-500/10 text-amber-300'

  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-semibold ${tone}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}{low ? <span className="ml-1 text-red-300">· Low Attendance</span> : null}{row.reconciliation_state === 'CONFLICT' ? <span className="ml-1 text-red-300">· Identity conflict</span> : null}
    </span>
  )
}

export function AttendanceMeter({ value }: { value: number | null }) {
  const tone = value !== null && value < 75
    ? 'bg-[#fb5364]'
    : value !== null && value < 85
      ? 'bg-[#ffc43d]'
      : 'bg-[#16c992]'
  const textTone = value === null
    ? 'text-slate-500'
    : value < 75
      ? 'text-red-300'
      : value < 85
        ? 'text-amber-300'
        : 'text-emerald-300'

  return (
    <div className="flex min-w-[120px] items-center gap-2">
      <span className={`w-10 text-[11px] font-semibold ${textTone}`}>
        {value === null || !Number.isFinite(value) ? '—' : `${value.toFixed(2)}%`}
      </span>
      <span className="h-1.5 w-[72px] overflow-hidden rounded-full bg-[#24384d]">
        <span
          className={`block h-full rounded-full ${tone}`}
          style={{ width: value === null ? '0%' : `${Math.max(0, Math.min(value, 100))}%` }}
        />
      </span>
    </div>
  )
}

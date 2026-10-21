import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CalendarDays,
  Check,
  Clock3,
  Download,
  Ellipsis,
  GraduationCap,
  Plus,
  Search,
  Upload,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react'
import { type FacultyAttendanceRosterRow } from '../../../../services/faculty/facultyAttendanceApi.ts'
import { type ImportedStats, type UploadStep } from '../state/workspaceTypes.ts'
export const surface =
  'rounded-lg border border-[#1e3348] bg-[linear-gradient(135deg,#0d1c2c_0%,#0b1826_100%)] shadow-[0_10px_24px_rgba(2,8,23,0.12)]'

export const input =
  'h-9 rounded-md border border-[#263d55] bg-[#091725] px-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-[#ffc72c] focus:ring-1 focus:ring-[#ffc72c]'

export const PAGE_SIZE = 25

export type GlyphName =
  | 'search'
  | 'download'
  | 'plus'
  | 'upload'
  | 'more'
  | 'users'
  | 'calendar'
  | 'chart'
  | 'clock'
  | 'check'
  | 'alert'
  | 'close'
  | 'back'

export const GLYPHS: Record<GlyphName, LucideIcon> = {
  search: Search,
  download: Download,
  plus: Plus,
  upload: Upload,
  more: Ellipsis,
  users: Users,
  calendar: CalendarDays,
  chart: BarChart3,
  clock: Clock3,
  check: Check,
  alert: AlertTriangle,
  close: X,
  back: ArrowLeft,
}

export function Glyph({ name, size = 18 }: { name: GlyphName; size?: number }) {
  const Icon = GLYPHS[name]
  return <Icon aria-hidden="true" size={size} strokeWidth={1.8} />
}

export function formatPercent(value: number | null) {
  return value === null || !Number.isFinite(value) ? '—' : `${value.toFixed(2)}%`
}

export function importedStats(row: FacultyAttendanceRosterRow): ImportedStats {
  return {
    percentage: row.attendance_percentage ?? null,
    present: row.present ?? null,
    absent: row.absent ?? null,
    classes: row.record_count ?? null,
  }
}

export function Stepper({ active, success = false }: { active: UploadStep; success?: boolean }) {
  const steps = ['Upload', 'Validate', 'Review', 'Import']
  return (
    <div className="grid grid-cols-4 gap-2 border-b border-[#1e3348] pb-5">
      {steps.map((label, index) => {
        const number = (index + 1) as UploadStep
        const complete = number < active || success
        const current = number === active && !success
        return (
          <div key={label} className="relative text-center">
            <div
              className={`mx-auto flex h-7 w-7 items-center justify-center rounded-full border text-xs font-bold ${complete ? 'border-emerald-400 bg-emerald-500 text-[#06131f]' : current ? 'border-[#ffc72c] bg-[#ffc72c] text-[#111a21]' : 'border-[#506984] bg-[#102235] text-slate-400'}`}
            >
              {complete ? <Glyph name="check" size={14} /> : number}
            </div>
            {index < steps.length - 1 ? (
              <span
                className={`absolute left-[58%] right-[-42%] top-3 h-px ${complete ? 'bg-emerald-400' : 'bg-[#30465c]'}`}
              />
            ) : null}
            <p
              className={`mt-2 text-[11px] ${current ? 'font-semibold text-[#ffc72c]' : complete ? 'text-emerald-300' : 'text-slate-500'}`}
            >
              {label}
            </p>
          </div>
        )
      })}
    </div>
  )
}

export function EmptyAssignment() {
  return (
    <section className={`${surface} flex min-h-[420px] flex-col items-center justify-center px-6 py-14 text-center`}>
      <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-[#17293d] text-[#ffc72c]">
        <GraduationCap aria-hidden="true" className="h-[42px] w-[42px]" strokeWidth={1.7} />
      </div>
      <h2 className="text-xl font-bold text-white">No Active Assignments</h2>
      <p className="mt-3 max-w-md text-sm leading-6 text-slate-400">
        You currently don't have any active course/section assignments. Once an administrator assigns you to a section,
        your attendance classes will appear here.
      </p>
    </section>
  )
}

export function ProfileStat({ label, value }: { label: string; value: number | null | string }) {
  return (
    <div className="rounded-lg border border-[#1e3348] bg-[#091725] p-3">
      <p className="text-lg font-bold text-white">{value === null ? '—' : value}</p>
      <p className="mt-1 text-[10px] text-slate-500">{label}</p>
    </div>
  )
}

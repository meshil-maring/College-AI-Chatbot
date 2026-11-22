/** Greeting, today's date and the current term for the student dashboard. */

import { CalendarDays } from 'lucide-react'
import type { StudentSemester } from '../../../types/semesterRegistration.ts'
import type { DashboardRead } from './useDashboardData.ts'

export function greetingFor(hour: number): string {
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function DashboardHeader({
  semester,
  now = new Date(),
}: {
  semester: DashboardRead<StudentSemester | null>
  now?: Date
}) {
  const today = now.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
  const term = semester.data
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="ui-eyebrow">Dashboard</p>
        <h1 className="text-page font-bold text-content">
          {greetingFor(now.getHours())} <span aria-hidden="true">👋</span>
        </h1>
        <p className="mt-1 text-sm text-muted">Your academic hub for learning, updates and college services.</p>
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-sm">
        <CalendarDays aria-hidden="true" className="h-5 w-5 shrink-0 text-accent" />
        <span className="font-semibold text-content">{today}</span>
        {term ? (
          <>
            <span aria-hidden="true" className="h-5 w-px bg-line" />
            <span className="text-content">
              {term.program_semester_name} · {term.term_name}
            </span>
          </>
        ) : null}
      </div>
    </header>
  )
}

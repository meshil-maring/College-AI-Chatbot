/** Top row of summary cards: program, semester, attendance and CGPA. */

import type { ReactNode } from 'react'
import { FileText, GraduationCap, Layers, Percent, type LucideIcon } from 'lucide-react'
import type { StudentSemester } from '../../../types/semesterRegistration.ts'
import { ComingSoonBadge } from './DashboardPanel.tsx'
import { termProgress, type DashboardRead } from './useDashboardData.ts'

function StatCard({ icon: Icon, label, children }: { icon: LucideIcon; label: string; children: ReactNode }) {
  return (
    <section
      aria-label={label}
      className="flex min-w-0 items-center gap-4 rounded-xl border border-line bg-surface p-4 sm:p-5"
    >
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-warning-bg text-accent">
        <Icon aria-hidden="true" className="h-6 w-6" />
      </span>
      <div className="min-w-0 flex-1">{children}</div>
    </section>
  )
}

function Placeholder({ read, unavailable }: { read: DashboardRead<unknown>; unavailable: string }) {
  const text = read.status === 'loading' ? 'Loading…' : read.status === 'error' ? 'Unable to load' : unavailable
  return <p className="mt-1 text-sm text-muted">{text}</p>
}

function ProgramCard({ semester }: { semester: DashboardRead<StudentSemester | null> }) {
  const term = semester.data
  return (
    <StatCard icon={GraduationCap} label="Program">
      <p className="text-xs text-muted">Program</p>
      {term ? (
        <>
          <p className="truncate text-card font-bold text-content" title={term.program_name}>
            {term.program_name}
          </p>
          <p className="truncate text-sm text-muted">
            {term.batch_name} · Section {term.section_name}
          </p>
        </>
      ) : (
        <Placeholder read={semester} unavailable="Not assigned yet" />
      )}
    </StatCard>
  )
}

function SemesterCard({ semester }: { semester: DashboardRead<StudentSemester | null> }) {
  const term = semester.data
  const progress = term ? termProgress(term) : null
  return (
    <StatCard icon={Layers} label="Semester">
      <p className="text-xs text-muted">Semester</p>
      {term ? (
        <>
          <p className="truncate text-card font-bold text-content">{term.program_semester_name}</p>
          {progress !== null ? (
            <div className="mt-2 flex items-center gap-2">
              <div
                role="progressbar"
                aria-label="Term progress"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
                className="h-2 flex-1 overflow-hidden rounded-full bg-raised"
              >
                <div className="h-full rounded-full bg-accent" style={{ width: `${progress}%` }} />
              </div>
              <span className="text-xs text-muted">{progress}%</span>
            </div>
          ) : null}
        </>
      ) : (
        <Placeholder read={semester} unavailable="Not assigned yet" />
      )}
    </StatCard>
  )
}

function ComingSoonCard({ icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <StatCard icon={icon} label={label}>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-card font-bold text-muted" aria-hidden="true">
        —
      </p>
      <div className="mt-1">
        <ComingSoonBadge />
      </div>
    </StatCard>
  )
}

export default function DashboardStats({ semester }: { semester: DashboardRead<StudentSemester | null> }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <ProgramCard semester={semester} />
      <SemesterCard semester={semester} />
      <ComingSoonCard icon={Percent} label="Attendance" />
      <ComingSoonCard icon={FileText} label="CGPA" />
    </div>
  )
}

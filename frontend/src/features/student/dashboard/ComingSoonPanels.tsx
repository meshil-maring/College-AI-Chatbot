/**
 * Dashboard panels whose student APIs do not exist yet: timetable,
 * deadlines and per-subject attendance. They show a clear "Coming soon"
 * label instead of placeholder numbers.
 */

import { BarChart3, CalendarDays, Clock } from 'lucide-react'
import type { StudentSemester } from '../../../types/semesterRegistration.ts'
import { ComingSoon, ComingSoonBadge, DashboardPanel, ViewAllButton } from './DashboardPanel.tsx'

export function TodaySchedule() {
  return (
    <DashboardPanel
      icon={CalendarDays}
      title="Today's Schedule"
      headingId="dashboard-schedule"
      action={<ViewAllButton label="View full schedule" />}
    >
      <ComingSoon message="Your class timetable will appear here once schedules are published." />
    </DashboardPanel>
  )
}

export function UpcomingDeadlines() {
  return (
    <DashboardPanel icon={Clock} title="Upcoming Deadlines" headingId="dashboard-deadlines" action={<ViewAllButton />}>
      <ComingSoon message="Assignment and lab submission deadlines will appear here." />
    </DashboardPanel>
  )
}

/** Lists the enrolled subjects, with attendance itself marked as coming soon. */
export function SubjectAttendance({ semester }: { semester: StudentSemester | null }) {
  const subjects = semester?.enrolled_subjects ?? []
  return (
    <DashboardPanel
      icon={BarChart3}
      title="Subject Attendance"
      headingId="dashboard-subject-attendance"
      action={subjects.length > 0 ? <ComingSoonBadge /> : undefined}
    >
      {subjects.length === 0 ? (
        <ComingSoon message="Attendance for each subject will appear here." />
      ) : (
        <ul className="space-y-3">
          {subjects.map((subject) => (
            <li key={subject.course_id} className="flex min-w-0 items-center gap-3 text-sm">
              <span className="min-w-0 flex-1 truncate text-content" title={subject.name}>
                {subject.name}
                {subject.code ? <span className="text-muted"> ({subject.code})</span> : null}
              </span>
              <span aria-hidden="true" className="h-2 w-24 shrink-0 rounded-full bg-raised" />
              <span className="w-10 shrink-0 text-right text-muted">—</span>
            </li>
          ))}
        </ul>
      )}
    </DashboardPanel>
  )
}

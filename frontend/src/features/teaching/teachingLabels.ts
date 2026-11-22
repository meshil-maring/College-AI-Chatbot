import type { TeachingAssignment, TeachingFacultyOption, TeachingOfferingLabel } from '../../types/teaching.ts'

export function offeringLabel(item: TeachingOfferingLabel) {
  const semester = item.semester_name ? ` · ${item.semester_name}` : ''
  return `${item.subject_name} (${item.subject_code}) · ${item.section_name}${semester}`
}

export function assignmentLabel(item: TeachingAssignment) {
  return `${item.subject_name} (${item.section_code})`
}

export const STATUS_LABEL: Record<TeachingAssignment['status'], string> = {
  pending: 'Awaiting HOD approval',
  active: 'Teaching',
  rejected: 'Rejected',
  cancelled: 'Withdrawn',
  ended: 'Ended',
}

/** The status shown to people: an active row past its planned end has ended. */
export function shownStatus(item: TeachingAssignment): TeachingAssignment['status'] {
  return item.status === 'active' && !item.is_current ? 'ended' : item.status
}

/** A calendar date (YYYY-MM-DD) or timestamp, shown without shifting the day. */
export function formatDay(value: string | null) {
  if (!value) return ''
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString(undefined, {
    dateStyle: 'medium',
    timeZone: 'UTC',
  })
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

/**
 * What the server will do with this choice, so the form can say so before
 * sending: assign at once, send for approval, or refuse (outside the viewer's
 * departments). The server still decides.
 */
export function assignmentOutcome(
  offering: TeachingOfferingLabel,
  teacher: TeachingFacultyOption,
  isAdmin: boolean,
  heads: readonly string[],
): 'active' | 'pending' | 'refused' {
  const homeHere = teacher.department_ids.includes(offering.department_id)
  const headsHere = heads.includes(offering.department_id)
  if (!isAdmin && !headsHere && !teacher.department_ids.some((id) => heads.includes(id))) return 'refused'
  return homeHere || headsHere ? 'active' : 'pending'
}

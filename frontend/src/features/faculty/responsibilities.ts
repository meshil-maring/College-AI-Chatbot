import type { FacultyContext, FacultyResponsibility } from '../../types/faculty.ts'

// Presentation only. Requests always re-authorize on the server.
export function visibleResponsibilities(context?: FacultyContext, now = Date.now()): FacultyResponsibility[] {
  return (context?.responsibilities ?? []).filter((row) => row.effective_active && row.is_active && !row.revoked_at
    && Date.parse(row.start_at) <= now && (!row.end_at || now < Date.parse(row.end_at)))
}

export function responsibilityPermissions(context?: FacultyContext): string[] {
  return [...new Set(visibleResponsibilities(context).flatMap((row) => row.permissions))]
}

export function validityLabel(row: { start_at: string; end_at: string | null }): string {
  const date = (value: string) => new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  return `${date(row.start_at)} → ${row.end_at ? date(row.end_at) : 'No end date'}`
}

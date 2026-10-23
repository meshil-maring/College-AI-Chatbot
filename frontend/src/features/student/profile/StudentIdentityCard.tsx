/** Read-only account identifiers and institution identity from /students/me/profile.
 * Internal database keys, credentials and retired academic fields are never rendered.
 */

import type { StudentIdentityProfile } from '../../../types/student.ts'
import type { StudentResourceState } from '../shared/useStudentResource.ts'
import { Definition, EmptyBlock, ErrorBlock, LoadingBlock } from '../shared/SectionState.tsx'
import { formatLabel, formatText } from '../shared/studentFormat.ts'

/** Preferred display identifier, in the order the backend exposes them. */
function preferredIdentifier(profile: StudentIdentityProfile): string | null {
  const candidates = [profile.register_number, profile.university_roll_number, profile.student_number]
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim() !== '') return candidate.trim()
  }
  return null
}

function safeField(value: unknown): string {
  return formatText(value)
}

export default function StudentIdentityCard({ profile }: { profile: StudentResourceState<StudentIdentityProfile> }) {
  if (profile.status === 'loading' || profile.status === 'idle') {
    return <LoadingBlock label="Loading your profile…" />
  }

  if (profile.status === 'error') {
    return <ErrorBlock message={profile.error ?? 'Unable to load your profile.'} onRetry={profile.reload} />
  }

  const data = profile.data
  if (data === null || data === undefined || typeof data !== 'object') {
    return <EmptyBlock message="Your profile is not available yet." />
  }

  const identifier = preferredIdentifier(data as StudentIdentityProfile)

  return (
    <>
      <p className="break-words text-sm text-slate-300">Welcome{identifier ? `, ${identifier}` : ''}</p>
      <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Definition label="Email" value={safeField(data.email)} />
        <Definition label="Register number" value={safeField(data.register_number)} />
        <Definition label="University roll number" value={safeField(data.university_roll_number)} />
        <Definition label="Student number" value={safeField(data.student_number)} />
        <Definition label="Institution" value={safeField(data.institution_name)} />
        <Definition label="Institution code" value={safeField(data.institution_code)} />
        <Definition label="Account status" value={formatLabel(data.status)} />
        <Definition label="Approval status" value={formatLabel(data.approval_status)} />
      </dl>
    </>
  )
}

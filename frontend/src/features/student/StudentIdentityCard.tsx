/**
 * Phase 6.16 — Student identity summary.
 *
 * Renders ONLY fields the authenticated backend contract actually returns
 * (`GET /api/v1/students/me/academic-profile`, Phase 6.14.1):
 *
 *   student_number, register_number, university_roll_number, email,
 *   institution_name, institution_code, status, approval_status
 *
 * Never rendered: internal database identifiers (`student_id`, `user_id`,
 * `institution_id`, `program_id`, `academic_year_id`, `auth_user_id`), tokens,
 * or authentication/service identifiers. Those values are not even in the
 * frontend type, so they cannot leak into the DOM.
 *
 * KNOWN GAP (documented, not worked around): the `students` table carries no
 * verified name column, so neither this contract nor the Phase 6.14.1 academic
 * profile exposes a full name. The card therefore greets the student by their
 * academic identifier instead of fabricating a name.
 */

import type { StudentAcademicProfile } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { Definition, EmptyBlock, ErrorBlock, LoadingBlock } from './SectionState.tsx'
import { formatLabel, formatText } from './studentFormat.ts'

/** Preferred display identifier, in the order the backend exposes them. */
function preferredIdentifier(profile: StudentAcademicProfile): string | null {
  const candidates = [profile.register_number, profile.university_roll_number, profile.student_number]
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim() !== '') return candidate.trim()
  }
  return null
}

function safeField(value: unknown): string {
  return formatText(value)
}

export default function StudentIdentityCard({
  profile,
}: {
  profile: StudentResourceState<StudentAcademicProfile>
}) {
  if (profile.status === 'loading' || profile.status === 'idle') {
    return <LoadingBlock label="Loading your profile…" />
  }

  if (profile.status === 'error') {
    return (
      <ErrorBlock
        message={profile.error ?? 'Unable to load your academic profile.'}
        onRetry={profile.reload}
      />
    )
  }

  const data = profile.data
  if (data === null || data === undefined || typeof data !== 'object') {
    return <EmptyBlock message="Your academic profile is not available yet." />
  }

  const identifier = preferredIdentifier(data as StudentAcademicProfile)

  return (
    <>
      <p className="break-words text-sm text-slate-300">
        Welcome{identifier ? `, ${identifier}` : ''}
      </p>
      <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Definition label="Email" value={safeField(data.email)} />
        <Definition label="Register number" value={safeField(data.register_number)} />
        <Definition
          label="University roll number"
          value={safeField(data.university_roll_number)}
        />
        <Definition label="Student number" value={safeField(data.student_number)} />
        <Definition
          label="Institution"
          value={safeField(data.institution_name)}
        />
        <Definition
          label="Institution code"
          value={safeField(data.institution_code)}
        />
        <Definition label="Enrollment status" value={formatLabel(data.status)} />
        <Definition label="Approval status" value={formatLabel(data.approval_status)} />
      </dl>
    </>
  )
}

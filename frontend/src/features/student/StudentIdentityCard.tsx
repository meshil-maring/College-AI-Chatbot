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
import { Definition, EmptyBlock, ErrorBlock, LoadingBlock, NOT_PROVIDED } from './SectionState.tsx'
import { formatLabel } from './studentFormat.ts'

/** Preferred display identifier, in the order the backend exposes them. */
function preferredIdentifier(profile: StudentAcademicProfile): string | null {
  return (
    profile.register_number?.trim() ||
    profile.university_roll_number?.trim() ||
    profile.student_number?.trim() ||
    null
  )
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
  if (data === null) {
    return <EmptyBlock message="Your academic profile is not available yet." />
  }

  const identifier = preferredIdentifier(data)

  return (
    <>
      <p className="text-sm text-slate-300">
        Welcome{identifier ? `, ${identifier}` : ''}
      </p>
      <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Definition label="Email" value={data.email?.trim() || NOT_PROVIDED} />
        <Definition label="Register number" value={data.register_number?.trim() || NOT_PROVIDED} />
        <Definition
          label="University roll number"
          value={data.university_roll_number?.trim() || NOT_PROVIDED}
        />
        <Definition label="Student number" value={data.student_number?.trim() || NOT_PROVIDED} />
        <Definition
          label="Institution"
          value={data.institution_name?.trim() || NOT_PROVIDED}
        />
        <Definition
          label="Institution code"
          value={data.institution_code?.trim() || NOT_PROVIDED}
        />
        <Definition label="Enrollment status" value={formatLabel(data.status)} />
        <Definition label="Approval status" value={formatLabel(data.approval_status)} />
      </dl>
    </>
  )
}

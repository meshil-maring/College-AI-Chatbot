/**
 * Phase 6.16 — Academic context summary.
 *
 * Shows the student's CURRENT academic context from the existing
 * `GET /api/v1/students/me/academic-profile` contract, which the backend
 * already resolves server-side (Phase 6.14.1):
 *
 *   institution_name / institution_code
 *   program_name / program_code
 *   academic_year_name / academic_year_code
 *   current_semester_name / current_semester_code
 *
 * Nothing is fabricated. Context the project does NOT yet expose — department,
 * year of study, section — is deliberately absent rather than guessed, and any
 * field the backend returns as `null` renders as an explicit "not provided"
 * dash instead of an invented value.
 *
 * Reuses the SAME already-loaded profile resource as the identity card: the
 * dashboard makes one `academic-profile` request for both sections.
 */

import type { StudentAcademicProfile } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { Definition, EmptyBlock, ErrorBlock, LoadingBlock, NOT_PROVIDED } from './SectionState.tsx'

function labelWithCode(name: unknown, code: unknown): string {
  const cleanName = typeof name === 'string' ? name.trim() : ''
  const cleanCode = typeof code === 'string' ? code.trim() : ''
  if (cleanName !== '' && cleanCode !== '') return `${cleanName} (${cleanCode})`
  return cleanName !== '' ? cleanName : cleanCode !== '' ? cleanCode : NOT_PROVIDED
}

export default function AcademicContextCard({
  profile,
}: {
  profile: StudentResourceState<StudentAcademicProfile>
}) {
  if (profile.status === 'loading' || profile.status === 'idle') {
    return <LoadingBlock label="Loading your academic context…" />
  }

  if (profile.status === 'error') {
    return (
      <ErrorBlock
        message={profile.error ?? 'Unable to load your academic context.'}
        onRetry={profile.reload}
      />
    )
  }

  const data = profile.data
  if (data === null || data === undefined || typeof data !== 'object') {
    return <EmptyBlock message="Your academic context is not available yet." />
  }

  return (
    <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <Definition
        label="Institution"
        value={labelWithCode(data.institution_name, data.institution_code)}
      />
      <Definition label="Program" value={labelWithCode(data.program_name, data.program_code)} />
      <Definition
        label="Academic year"
        value={labelWithCode(data.academic_year_name, data.academic_year_code)}
      />
      <Definition
        label="Current semester"
        value={labelWithCode(data.current_semester_name, data.current_semester_code)}
      />
    </dl>
  )
}

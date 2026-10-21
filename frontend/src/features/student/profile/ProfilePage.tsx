import { getMyAcademicProfile } from '../../../services/students/studentApi.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'
import { SectionCard } from '../shared/SectionState.tsx'
import StudentIdentityCard from './StudentIdentityCard.tsx'
import AcademicContextCard from '../shared/AcademicContextCard.tsx'

/**
 * Phase 6.16.3 — Profile page (READ-ONLY BY DESIGN). The backend exposes NO
 * student-owned profile-update contract (every `PATCH /students/*` route is
 * admin-only), so no edit UI exists here and none was invented. Identity and
 * academic context come from the single `GET /students/me/academic-profile`
 * request, shared by both cards below — one request per profile mount.
 */
export function ProfilePage() {
  const profile = useStudentResource(
    getMyAcademicProfile,
    'Unable to load your academic profile.',
    '',
    'academic-profile',
  )
  return (
    <div className="space-y-4">
      <SectionCard title="Your profile" headingId="student-page-profile">
        <StudentIdentityCard profile={profile} />
      </SectionCard>
      {profile.status !== 'loading' ? (
        <SectionCard title="Academic context" headingId="student-page-context">
          <AcademicContextCard profile={profile} />
        </SectionCard>
      ) : null}
    </div>
  )
}

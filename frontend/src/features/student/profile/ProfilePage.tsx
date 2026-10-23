import type { StudentIdentityProfile } from '../../../types/student.ts'
import type { StudentResourceState } from '../shared/useStudentResource.ts'
import { SectionCard } from '../shared/SectionState.tsx'
import StudentIdentityCard from './StudentIdentityCard.tsx'
import { getMyProfile } from '../../../services/students/studentApi.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'

export function ProfilePage({ profile }: { profile?: StudentResourceState<StudentIdentityProfile> }) {
  return profile ? <IdentitySection profile={profile} /> : <ProfileResource />
}
function ProfileResource() {
  const profile = useStudentResource(getMyProfile, 'Unable to load your profile.', '', 'identity-profile')
  return <IdentitySection profile={profile} />
}
function IdentitySection({ profile }: { profile: StudentResourceState<StudentIdentityProfile> }) {
  return (
    <SectionCard headingId="student-identity-heading" title="Student identity">
      <StudentIdentityCard profile={profile} />
    </SectionCard>
  )
}

import type { CurrentUser } from '../../../types/auth.ts'
import FacultyIdentityCard from './FacultyIdentityCard.tsx'

export default function FacultyProfile({ user }: { user: CurrentUser }) {
  return <FacultyIdentityCard user={user} />
}

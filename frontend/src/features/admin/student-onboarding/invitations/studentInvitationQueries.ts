import { queryClient } from '../../../../lib/queryClient.ts'
import { invalidateStudentDirectory } from '../../students/directory/studentDirectoryQueries.ts'

export const invitationKey = (identity: string) => ['admin', identity, 'student-onboarding-invitations'] as const

/** New or changed invitations also appear in All Students. */
export function refreshStudentInvitations(identity: string) {
  void queryClient.invalidateQueries({ queryKey: invitationKey(identity) })
  void invalidateStudentDirectory()
}

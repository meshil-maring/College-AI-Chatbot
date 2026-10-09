import { queryClient } from '../../lib/queryClient.ts'

export const adminAcademicKeys = {
  setup: (token: string) => ['admin', 'academic-setup', token] as const,
  assignments: (token: string) => ['admin', 'faculty-assignments', token] as const,
  responsibilities: (token: string) => ['admin', 'responsibilities', token] as const,
}

export function invalidateFacultyResponsibilities(token: string): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: adminAcademicKeys.responsibilities(token) })
}

/** Academic edits can change eligible sections, subject labels and responsibility scopes. */
export async function invalidateFacultyAcademicOptions(token: string): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: adminAcademicKeys.assignments(token) }),
    invalidateFacultyResponsibilities(token),
  ])
}

import { queryOptions } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY } from '../../../lib/queryClient.ts'
import { getMySemesters } from '../../../services/academics/semesterRegistration.ts'

export const studentRegistrationKey = (identity: string) => ['academics', identity, 'own-registration'] as const
export function studentRegistrationOptions(identity: string, institutionId: string, token: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: studentRegistrationKey(identity),
    queryFn: async ({ signal }) => {
      const result = await getMySemesters(token, signal)
      if (result.institution_id !== institutionId)
        throw new Error('Registration data is unavailable for this institution.')
      return result
    },
  })
}

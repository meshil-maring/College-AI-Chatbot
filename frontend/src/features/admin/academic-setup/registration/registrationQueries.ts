import { queryOptions } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY } from '../../../../lib/queryClient.ts'
import { getRegistrationCatalogue } from '../../../../services/academics/semesterRegistration.ts'
import type { StructureContext } from '../structure/useAcademicStructure.ts'

export const registrationKeys = {
  admin: (identity: string) => ['academics', identity, 'registration'] as const,
}
export function registrationCatalogueOptions(context: StructureContext) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: registrationKeys.admin(context.identity),
    enabled: context.canReadCatalogues,
    queryFn: async ({ signal }) => {
      const data = await getRegistrationCatalogue(context.accessToken, signal)
      if (data.institution_id !== context.institutionId)
        throw new Error('Registration data does not belong to this institution.')
      return data
    },
  })
}

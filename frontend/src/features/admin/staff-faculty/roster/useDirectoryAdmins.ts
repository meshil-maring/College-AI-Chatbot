import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import { listInstitutionAdmins } from '../../../../services/admin/adminApi.ts'
import { staffFacultyKeys } from '../staffFacultyKeys.ts'

/**
 * Administrators for the user directory. Shares its cache with the
 * Administrators page; if they cannot be loaded the directory still lists
 * Staff, Faculty and invitations.
 */
export function useDirectoryAdmins(accessToken: string) {
  const query = useQuery(
    {
      queryKey: staffFacultyKeys.administrators(accessToken),
      queryFn: () => listInstitutionAdmins(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  return query.data?.administrators ?? []
}

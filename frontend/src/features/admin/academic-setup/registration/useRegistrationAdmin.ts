import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { queryClient } from '../../../../lib/queryClient.ts'
import { AdminApiError } from '../../../../services/admin/http.ts'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import { registrationCatalogueOptions } from './registrationQueries.ts'

export function useRegistrationAdmin(context: StructureContext) {
  const query = useQuery(registrationCatalogueOptions(context), queryClient)
  const [notice, setNotice] = useState('')
  const mounted = useRef(true)
  const locked = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const mutation = useMutation(
    {
      mutationFn: async (operation: () => Promise<{ institution_id: string }>) => {
        const result = await operation()
        if (result.institution_id !== context.institutionId) throw new Error('The saved record could not be verified.')
        return result
      },
      onSuccess: async () => {
        if (!mounted.current) return
        setNotice('Saved successfully.')
        await queryClient.invalidateQueries({ queryKey: registrationCatalogueOptions(context).queryKey })
      },
    },
    queryClient,
  )
  const denied = query.error instanceof AdminApiError && [401, 403].includes(query.error.status)
  const data = denied ? undefined : query.data
  async function save(operation: () => Promise<{ institution_id: string }>) {
    if (!mounted.current || locked.current || query.isFetching || query.isError) return false
    locked.current = true
    setNotice('')
    try {
      await mutation.mutateAsync(operation)
      return mounted.current
    } catch {
      return false
    } finally {
      locked.current = false
    }
  }
  return {
    query,
    data,
    save,
    saving: mutation.isPending,
    notice,
    error: query.error ?? mutation.error,
    busy: query.isFetching || query.isError || mutation.isPending || !data,
  }
}

import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { queryClient } from '../../lib/queryClient.ts'
import { commandAcademicPackage, getAcademicPackages } from '../../services/academics/academicPackagesApi.ts'
import type { AcademicPackageCommands, PackageOperation } from '../../types/academicPackages.ts'
import { rows, value } from './packagePresentation.ts'

export function useAcademicPackages(token: string) {
  const client = queryClient
  const [notice, setNotice] = useState('')
  const key = ['academic-packages', token]
  const query = useQuery(
    { queryKey: key, queryFn: ({ signal }) => getAcademicPackages(token, signal), staleTime: 30_000, retry: false },
    client,
  )
  const mutation = useMutation(
    {
      mutationFn: ({
        operation,
        payload,
      }: {
        operation: PackageOperation
        payload: AcademicPackageCommands[PackageOperation]
      }) => commandAcademicPackage(token, operation, payload),
      onSuccess: async () => {
        setNotice('Saved. The latest subject assignments and rules are shown below.')
        await client.invalidateQueries({ queryKey: key })
        await client.invalidateQueries({
          predicate: (query) => query.queryKey.includes(token) && query.queryKey[0] !== 'academic-packages',
        })
      },
    },
    client,
  )
  useEffect(() => {
    if (!query.data) return
    const deadlines = rows(query.data, 'classes')
      .map((row) => Date.parse(value(row, 'change_cutoff')))
      .filter((time) => time > Date.now())
    if (!deadlines.length) return
    const delay = Math.min(Math.min(...deadlines) - Date.now() + 50, 2_147_483_647)
    const timer = window.setTimeout(() => void query.refetch(), Math.max(delay, 1))
    return () => window.clearTimeout(timer)
  }, [query.data, query.refetch])
  async function run<K extends PackageOperation>(operation: K, payload: AcademicPackageCommands[K]) {
    setNotice('')
    await mutation.mutateAsync({ operation, payload })
  }
  return {
    query,
    data: query.data,
    run,
    notice,
    busy: mutation.isPending || query.isFetching,
    error: mutation.error,
    clearError: mutation.reset,
  }
}

export type PackageWorkspaceState = ReturnType<typeof useAcademicPackages>

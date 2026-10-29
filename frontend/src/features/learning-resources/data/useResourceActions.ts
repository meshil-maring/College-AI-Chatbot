import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../../../services/knowledge/resources.ts'
import type { ResourceRevision } from '../../../types/learningResources.ts'
import { accessDenied, resourceKeys, verifyRevision } from './queries.ts'
import type { ResourceContext } from './resourceIdentity.ts'

interface Options {
  context: ResourceContext
  isCurrent: () => boolean
  onAccessLost: () => void
}
export function useResourceActions({ context, isCurrent, onAccessLost }: Options) {
  const client = useQueryClient()
  const mounted = useRef(true)
  const locked = useRef(false)
  const [blocked, setBlocked] = useState(false)
  const [notice, setNotice] = useState('')
  const [activity, setActivity] = useState<'save' | 'upload' | 'retry' | 'review' | null>(null)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const current = () => mounted.current && isCurrent()
  const mutation = useMutation({
    mutationKey: [...resourceKeys.scope(context.identity), 'write'],
    retry: false,
    mutationFn: async (operation: () => Promise<ResourceRevision>) => {
      if (!current()) throw new Error('Retired resource identity')
      return verifyRevision(context, await operation())
    },
    onSuccess: async (revision) => {
      if (!current()) return
      client.setQueryData(resourceKeys.revision(context.identity, revision.revision_id), revision)
      setNotice('Changes saved.')
      // Publication also changes library access; never optimistically publish.
      await client.invalidateQueries({ queryKey: resourceKeys.scope(context.identity) })
    },
    onError: async (error) => {
      if (!current()) return
      if (accessDenied(error)) {
        onAccessLost()
        await client.cancelQueries({ queryKey: resourceKeys.scope(context.identity) })
        client.removeQueries({ queryKey: resourceKeys.scope(context.identity) })
      } else if (error instanceof api.ResourceApiError && error.code === 'RESOURCE_INDEXING_FAILED') {
        await client.invalidateQueries({ queryKey: resourceKeys.scope(context.identity) })
      } else if (!(error instanceof api.ResourceApiError) || [0, 409].includes(error.status) || error.status >= 500) {
        setBlocked(true)
      }
    },
  })
  async function run(operation: () => Promise<ResourceRevision>, kind: NonNullable<typeof activity> = 'save') {
    if (!current() || locked.current || blocked) return null
    locked.current = true
    setActivity(kind)
    setNotice('')
    try {
      const result = await mutation.mutateAsync(operation)
      return current() ? result : null
    } catch {
      return null
    } finally {
      locked.current = false
      if (current()) setActivity(null)
    }
  }
  return {
    run,
    blocked,
    notice,
    activity,
    saving: mutation.isPending,
    error: mutation.error ? api.resourceError(mutation.error) : '',
    indexingFailed:
      mutation.error instanceof api.ResourceApiError && mutation.error.code === 'RESOURCE_INDEXING_FAILED',
    clear: () => {
      mutation.reset()
      setBlocked(false)
      setNotice('')
    },
  }
}
export type ResourceActions = ReturnType<typeof useResourceActions>

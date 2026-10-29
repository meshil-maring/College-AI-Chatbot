import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { ResourceView } from '../../../types/learningResources.ts'
import { accessDenied, resourceListOptions } from './queries.ts'
import type { ResourceContext } from './resourceIdentity.ts'

export function useResources(context: ResourceContext) {
  const [view, setView] = useState<ResourceView>(context.canRead ? 'library' : context.canCreate ? 'own' : 'review')
  const [offset, setOffset] = useState(0)
  const [search, setSearch] = useState('')
  const [audience, setAudience] = useState('all')
  const [status, setStatus] = useState('all')
  const enabled = view === 'library' ? context.canRead : view === 'own' ? context.canCreate : context.canReview
  const query = useQuery({ ...resourceListOptions(context, view, offset), enabled })
  const denied = accessDenied(query.error)
  const data = denied ? undefined : query.data
  const rows = data?.items.filter(
    (row) =>
      `${row.title} ${row.description ?? ''} ${row.source_type}`.toLowerCase().includes(search.trim().toLowerCase()) &&
      (audience === 'all' || row.visibility === audience) &&
      (view === 'library' || status === 'all' || ('lifecycle_status' in row && row.lifecycle_status === status)),
  )
  function clearFilters() {
    setSearch('')
    setAudience('all')
    setStatus('all')
  }
  function changeView(next: ResourceView) {
    setView(next)
    setOffset(0)
    clearFilters()
  }
  return {
    query,
    denied,
    data,
    rows,
    view,
    offset,
    search,
    audience,
    status,
    enabled,
    setView: changeView,
    setOffset,
    setSearch,
    setAudience,
    setStatus,
    clearFilters,
  }
}
export type ResourcesState = ReturnType<typeof useResources>

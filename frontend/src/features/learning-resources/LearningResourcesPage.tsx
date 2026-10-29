import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { resourceContext } from './data/resourceIdentity.ts'
import { resourceKeys } from './data/queries.ts'
import ResourceWorkspace from './ResourceWorkspace.tsx'
import './styles/resources.css'

export default function LearningResourcesPage() {
  const { user, accessToken, sessionGeneration } = useAuth()
  const client = useQueryClient()
  const context = resourceContext(user, accessToken, sessionGeneration ?? 0)
  const live = useRef<string | null>(context?.identity ?? null)
  live.current = context?.identity ?? null
  const identity = context?.identity
  useEffect(
    () => () => {
      if (identity && live.current !== identity) {
        void client.cancelQueries({ queryKey: resourceKeys.scope(identity) })
        client.removeQueries({ queryKey: resourceKeys.scope(identity) })
      }
    },
    [client, identity],
  )
  if (!context)
    return (
      <section className="learning-resources-page lr-empty" role="status">
        <h1>Learning Resources</h1>
        <p>An active institution account with resource access is required.</p>
      </section>
    )
  return (
    <ResourceWorkspace key={context.identity} context={context} isCurrent={() => live.current === context.identity} />
  )
}

import { getMyResources } from '../../../services/students/studentApi.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'
import { SectionCard } from '../shared/SectionState.tsx'
import ResourcesPanel from './ResourcesPanel.tsx'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { hasPermission } from '../../auth/access/permissions.ts'
import AskResourceAi from '../../chat/resource/AskResourceAi.tsx'
import ResourceChatView from '../../chat/resource/ResourceChatView.tsx'
import type { ResourceChatContext } from '../../../types/chat.ts'

/**
 * Phase 6.16.3 — Learning Resources page. `20` stays well inside the backend's
 * resource limit contract (`student_resources.MAX_RESOURCE_LIMIT === 50`).
 * The endpoint returns safe metadata only — there is NO storage-access or
 * download contract. Ask AI separately confirms authorized, indexed resource
 * context without changing this safe metadata projection or its filters.
 */
export function ResourcesPage() {
  const { user, sessionGeneration } = useAuth()
  const identity = JSON.stringify([
    sessionGeneration,
    user?.user_id,
    user?.institution_id,
    [...(user?.effective_permissions ?? [])].sort(),
  ])
  return <ResourcePageSession key={identity} />
}

function ResourcePageSession() {
  const { accessToken, user } = useAuth()
  const active = useRef(true)
  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
    }
  }, [])
  const [selected, setSelected] = useState<ResourceChatContext | null>(null)
  const resources = useStudentResource(
    (token) => getMyResources(token, 20),
    'Unable to load learning resources.',
    '',
    'resources-20',
  )
  if (selected) return <ResourceChatView resource={selected} onBack={() => setSelected(null)} />
  return (
    <SectionCard title="Learning resources" headingId="student-page-resources">
      <ResourcesPanel
        resources={resources}
        renderAction={
          accessToken && hasPermission(user?.effective_permissions, 'ai.chat')
            ? (sourceId) => (
                <AskResourceAi
                  context={{ accessToken, canAsk: true }}
                  sourceId={sourceId}
                  disabled={false}
                  isCurrent={() => active.current}
                  onReady={setSelected}
                />
              )
            : undefined
        }
      />
    </SectionCard>
  )
}

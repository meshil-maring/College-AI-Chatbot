/** Keep the complete chat workspace scoped to the authenticated identity. */

import { useAuth } from '../auth/session/AuthProvider.tsx'
import ChatSession from './session/ChatSession.tsx'
import type { ResourceChatContext } from '../../types/chat.ts'

export default function ChatShell({ initialResource = null }: { initialResource?: ResourceChatContext | null }) {
  const { user, sessionGeneration } = useAuth()
  const identity = JSON.stringify([
    sessionGeneration,
    user?.user_id,
    user?.institution_id,
    user?.role,
    [...(user?.effective_permissions ?? [])].sort(),
    initialResource?.knowledge_source_id,
  ])
  return <ChatSession key={identity} identity={identity} initialResource={initialResource} />
}

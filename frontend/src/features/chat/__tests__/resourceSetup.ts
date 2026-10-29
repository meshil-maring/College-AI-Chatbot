import { beforeEach, vi } from 'vitest'
import { queryClient } from '../../../lib/queryClient.ts'
import * as api from '../../../services/chat/api.ts'

const auth = vi.hoisted(() => ({
  accessToken: 'private-token',
  sessionGeneration: 10,
  user: { user_id: 'user-a', institution_id: 'college-a', role: 'faculty', effective_permissions: ['*'] },
}))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => ({ ...auth, logout: vi.fn() }) }))
vi.mock('../../../services/chat/api.ts', async (original) => ({
  ...(await original<typeof import('../../../services/chat/api.ts')>()),
  chat: vi.fn(),
  listConversations: vi.fn(),
  getConversationMessages: vi.fn(),
}))
export const resource = { knowledge_source_id: 'source-a', title: 'Library guide', available: true }
export function reply() {
  return {
    session_id: 'session-a',
    conversation_id: 'conversation-a',
    message_id: 'message-a',
    answer: 'Borrow two books.',
    status: 'success' as const,
    sources: [],
    source_references: [],
    model_used: null,
    metadata: {},
    usage: null,
    resource_context: resource,
  }
}
beforeEach(() => {
  queryClient.clear()
  auth.user.user_id = 'user-a'
  auth.user.effective_permissions = ['*']
  auth.sessionGeneration = 10
  auth.accessToken = 'private-token'
  vi.mocked(api.chat).mockReset().mockResolvedValue(reply())
  vi.mocked(api.listConversations).mockReset().mockResolvedValue([])
  vi.mocked(api.getConversationMessages).mockReset().mockResolvedValue([])
})
export { auth }

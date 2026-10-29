import { queryOptions } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY } from '../../../lib/queryClient.ts'
import { getConversationMessages, listConversations } from '../../../services/chat/api.ts'

export function conversationListOptions(identity: string, token: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: ['conversations', identity] as const,
    staleTime: 0,
    queryFn: ({ signal }) => listConversations(token, signal),
  })
}
export function conversationMessagesOptions(identity: string, id: string, token: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: ['conversation-messages', identity, id] as const,
    staleTime: 0,
    queryFn: ({ signal }) => getConversationMessages(id, token, signal),
  })
}

import { queryOptions } from '@tanstack/react-query'
import { getChatTurn } from '../../../services/chat/recovery.ts'

export const turnKeys = {
  scope: (identity: string) => ['chat-recovery', identity] as const,
  status: (identity: string, turnId: string) => [...turnKeys.scope(identity), turnId] as const,
}

export function turnStatusOptions(identity: string, turnId: string, token: string) {
  return queryOptions({
    queryKey: turnKeys.status(identity, turnId),
    queryFn: ({ signal }) => getChatTurn(turnId, token, signal),
    staleTime: 0,
    gcTime: 0,
    retry: false,
    meta: { navigationCache: true },
  })
}

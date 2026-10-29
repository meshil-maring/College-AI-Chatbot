import type { ChatRequest, ChatResponse } from '../../types/chat.ts'
import { notifySessionExpired } from '../shared/sessionEvents.ts'
import { ApiError } from './api.ts'
import { withDeadline } from './deadline.ts'

const BASE = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export interface ChatTurnStatus {
  turn_id: string
  conversation_id: string
  state: 'processing' | 'failed' | 'completed'
  retryable: boolean
  retry_after_seconds: number
  request: ChatRequest
  response: ChatResponse | null
}

export function errorCode(failure: unknown): string | null {
  if (!(failure instanceof ApiError) || !failure.details || typeof failure.details !== 'object') return null
  const error = (failure.details as { error?: { code?: unknown } }).error
  return typeof error?.code === 'string' ? error.code : null
}

export function getChatTurn(turnId: string, accessToken: string, signal?: AbortSignal): Promise<ChatTurnStatus> {
  return withDeadline(
    15_000,
    async (signal) => {
      const response = await fetch(`${BASE}/v1/generation/turns/${encodeURIComponent(turnId)}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        signal,
      })
      if (!response.ok) {
        const details = await response.json().catch(() => undefined)
        if (response.status === 401) notifySessionExpired(accessToken)
        throw new ApiError(response.status, 'Could not check the saved reply.', details)
      }
      return (await response.json()) as ChatTurnStatus
    },
    signal,
  )
}

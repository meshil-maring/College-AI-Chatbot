/**
 * Phase 5.7 — Conversation history state boundary.
 *
 * Owns all persisted conversation history state for the chat feature:
 *   - conversations       (list of the authenticated user's conversations)
 *   - selectedConversationId (currently selected conversation, or null)
 *   - historyLoading      (while the conversation list is being fetched)
 *   - historyError        (user-safe error for conversation list failures)
 *   - messagesLoading     (while persisted messages are being fetched)
 *   - messagesError       (user-safe error for message fetch failures)
 *   - loadConversations() (fetch the authenticated user's conversations)
 *   - selectConversation() (select a conversation and load its messages)
 *   - clearSelection()    (deselect the current conversation)
 *
 * Architecture:
 *   AuthProvider (Phase 5.4)  ->  useConversationHistory  ->  api.ts (Phase 5.3/5.7)
 *       ->  GET /api/v1/conversations
 *       ->  GET /api/v1/conversations/{conversation_id}/messages  ->  FastAPI
 *
 * Rules enforced here:
 *   - The access token comes ONLY from the Phase 5.4 auth boundary.
 *   - No frontend UUID is fabricated for conversations.
 *   - Conversation IDs come exclusively from the backend.
 *   - No conversation history is persisted in localStorage.
 *   - On logout, all history state must be cleared by the consumer.
 */

import { useCallback, useState } from 'react'
import { ApiError, getConversationMessages, listConversations } from '../services/api.ts'
import type { ConversationSummary, MessageSummary } from '../types/conversation.ts'

/** User-safe errors. Never include tokens, stack traces, or backend internals. */
const SESSION_EXPIRED_MESSAGE: string =
  'Your session has expired or is no longer valid. Please sign out and sign in again.'
const PERMISSION_MESSAGE: string =
  'You do not have permission to view these conversations. Please sign out and sign in again.'
const VALIDATION_MESSAGE: string =
  'The server could not process the request. Please try again.'
const SERVER_MESSAGE: string =
  'The server reported an error while loading your conversations. Please try again in a moment.'
const NETWORK_MESSAGE: string =
  'Could not reach the server. Check that the backend is running, then try again.'

/** Map an error from the history API to a user-safe message. */
function historyErrorMessage(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return SESSION_EXPIRED_MESSAGE
    }
    if (caught.status === 403) {
      return PERMISSION_MESSAGE
    }
    if (caught.status === 422) {
      return VALIDATION_MESSAGE
    }
    if (caught.status === 404) {
      return 'The selected conversation could not be found. It may have been removed.'
    }
    if (caught.status >= 500) {
      return SERVER_MESSAGE
    }
    return caught.message
  }
  return NETWORK_MESSAGE
}

export interface ConversationHistoryState {
  /** The authenticated user's conversations, or null before the first load. */
  readonly conversations: ConversationSummary[]
  /** The currently selected conversation ID, or null. */
  readonly selectedConversationId: string | null
  /** True while the conversation list is being fetched. */
  readonly historyLoading: boolean
  /** User-safe error from the last failed list fetch, or null. */
  readonly historyError: string | null
  /** True while persisted messages are being fetched. */
  readonly messagesLoading: boolean
  /** User-safe error from the last failed message fetch, or null. */
  readonly messagesError: string | null
  /** Fetch the authenticated user's conversations. */
  readonly loadConversations: (accessToken: string) => Promise<void>
  /** Select a conversation and load its messages. */
  readonly selectConversation: (conversationId: string, accessToken: string) => Promise<MessageSummary[]>
  /** Deselect the current conversation and clear messages/errors. */
  readonly clearSelection: () => void
  /** Clear all history state (used on logout). */
  readonly clearAll: () => void
}

export function useConversationHistory(): ConversationHistoryState {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [messagesError, setMessagesError] = useState<string | null>(null)

  const loadConversations = useCallback(
    async (accessToken: string): Promise<void> => {
      setHistoryLoading(true)
      setHistoryError(null)
      try {
        const result = await listConversations(accessToken)
        setConversations(result)
      } catch (caught) {
        setHistoryError(historyErrorMessage(caught))
        setConversations([])
      } finally {
        setHistoryLoading(false)
      }
    },
    [],
  )

  const selectConversation = useCallback(
    async (conversationId: string, accessToken: string): Promise<MessageSummary[]> => {
      setSelectedConversationId(conversationId)
      setMessagesLoading(true)
      setMessagesError(null)
      try {
        const messages = await getConversationMessages(conversationId, accessToken)
        return messages
      } catch (caught) {
        setMessagesError(historyErrorMessage(caught))
        if (caught instanceof ApiError && caught.status === 404) {
          setSelectedConversationId(null)
        }
        throw caught
      } finally {
        setMessagesLoading(false)
      }
    },
    [],
  )

  const clearSelection = useCallback((): void => {
    setSelectedConversationId(null)
    setMessagesError(null)
    setMessagesLoading(false)
  }, [])

  const clearAll = useCallback((): void => {
    setConversations([])
    setSelectedConversationId(null)
    setHistoryLoading(false)
    setHistoryError(null)
    setMessagesLoading(false)
    setMessagesError(null)
  }, [])

  return {
    conversations,
    selectedConversationId,
    historyLoading,
    historyError,
    messagesLoading,
    messagesError,
    loadConversations,
    selectConversation,
    clearSelection,
    clearAll,
  }
}

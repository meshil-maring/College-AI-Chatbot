/**
 * Phase 5.5 — Dedicated chat state boundary.
 *
 * Owns all temporary in-browser conversation state for the chat feature:
 *   - messages          (presentation-oriented ChatMessage list)
 *   - isLoading         (one in-flight request at a time)
 *   - error             (user-safe error message, never secrets/stack traces)
 *   - sessionId         (opaque backend-created identifier)
 *   - conversationId    (opaque backend-created identifier)
 *   - sendMessage()     (single authenticated POST through the Phase 5.3 client)
 *   - resetChat()       (clears local chat state only — nothing server-side)
 *
 * Architecture (all intelligence stays in the backend):
 *   AuthProvider (Phase 5.4)  ->  useChat  ->  api.ts (Phase 5.3)
 *       ->  POST /api/v1/generation/chat  ->  FastAPI
 *
 * Rules enforced here:
 *   - The user query is trimmed; blank input never produces a request.
 *   - No request is sent while one is pending (no duplicate sends).
 *   - The access token comes ONLY from the Phase 5.4 auth boundary.
 *   - session_id / conversation_id are never invented: the first request
 *     omits them; later requests reuse exactly the values the backend returned.
 *   - The institution_id is the established demo institution constant.
 *   - No frontend-network path other than services/api.ts is used.
 */

import { useCallback, useState } from 'react'
import { ApiError, chat } from '../services/api.ts'
import { DEMO_INSTITUTION_ID } from '../features/chat/institution.ts'
import { useAuth } from '../features/auth/AuthProvider.tsx'
import type {
  ChatRequest,
  ChatResponse,
} from '../types/chat.ts'
import type { ChatMessage } from '../features/chat/chatTypes.ts'
import type { MessageSummary } from '../types/conversation.ts'

/** Defensive fallback when the backend reports success but no answer text. */
const EMPTY_ANSWER_FALLBACK: string =
  '(The server returned a successful response without answer text.)'

/** User-safe errors. Never include tokens, stack traces, or backend internals. */
const SESSION_EXPIRED_MESSAGE: string =
  'Your session has expired or is no longer valid. Please sign out and sign in again.'
const PERMISSION_MESSAGE: string =
  'You do not have permission to continue this conversation. Please start a new chat.'
const VALIDATION_MESSAGE: string =
  'The server could not validate the request. Please check your question and try again.'
const SERVER_MESSAGE: string =
  'The chatbot server reported an error. Please try again in a moment.'
const NETWORK_MESSAGE: string =
  'Could not reach the chatbot server. Check that the backend is running, then try again.'
const GENERIC_MESSAGE: string =
  'Something went wrong while sending your message. Please try again.'

/**
 * Frontend-only monotonic id source for React list keys.
 * Intentionally NOT crypto.randomUUID: session/conversation identifiers are
 * exclusively owned and created by the backend; this id is only a UI key.
 */
let nextMessageId = 1

function nextUiMessageId(): string {
  const id = `chat-msg-${nextMessageId}`
  nextMessageId += 1
  return id
}

/** Build the presentation message for one backend ChatResponse. */
function assistantMessageFrom(response: ChatResponse): ChatMessage {
  const content =
    response.status === 'success'
      ? (response.answer ?? EMPTY_ANSWER_FALLBACK)
      : ''
  return {
    id: nextUiMessageId(),
    role: 'assistant',
    content,
    status: response.status,
    sources: response.sources,
    sourceReferences: response.source_references,
    usage: response.usage,
    modelUsed: response.model_used,
  }
}

/** Map any failure to a user-safe message (never expose internals). */
function chatErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return SESSION_EXPIRED_MESSAGE
      case 403:
        return PERMISSION_MESSAGE
      case 422:
        return VALIDATION_MESSAGE
      default:
        return error.status >= 500 ? SERVER_MESSAGE : GENERIC_MESSAGE
    }
  }
  // A non-ApiError means fetch never produced an HTTP response
  // (connection refused, DNS failure, aborted request, ...).
  return NETWORK_MESSAGE
}

export interface ChatState {
  /** Chronological in-browser conversation (user / assistant / ...). */
  readonly messages: ChatMessage[]
  /** True while one chat request is pending. */
  readonly isLoading: boolean
  /** User-safe error from the last failed send, or null. */
  readonly error: string | null
  /** Opaque session id returned by the backend, or null before the first turn. */
  readonly sessionId: string | null
  /** Opaque conversation id returned by the backend, or null before the first turn. */
  readonly conversationId: string | null
  /** Send one trimmed question through the Phase 5.3 API client. */
  readonly sendMessage: (raw: string) => Promise<void>
  /** Clear local chat state (messages, ids, error). No backend/database effect. */
  readonly resetChat: () => void
  /**
   * Load a persisted conversation's messages into the chat state.
   *
   * Sets the conversation ID so the next message continues in the same
   * backend conversation. Does NOT set the session ID: the persisted history
   * API does not return it, and the backend will generate a new one on the
   * next chat request (the backend uses conversation_id for lookup).
   *
   * Maps persisted messages into the existing ChatMessage representation
   * so they render through the existing Phase 5.5 message components.
   */
  readonly loadConversation: (conversationId: string, messages: MessageSummary[]) => void
}

export function useChat(): ChatState {
  // Phase 5.4 AuthProvider is the authoritative frontend auth boundary.
  const { accessToken } = useAuth()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (raw: string): Promise<void> => {
      // Normalize + reject blank input before anything touches the network.
      const userQuery = raw.trim()
      if (userQuery.length === 0 || isLoading) {
        return
      }
      if (accessToken === null) {
        setError('You are not signed in. Please sign in to continue.')
        return
      }

      setError(null)
      setMessages((previous) => [
        ...previous,
        { id: nextUiMessageId(), role: 'user', content: userQuery },
      ])
      setIsLoading(true)

      // First request: omit session/conversation ids (the backend creates them).
      // Later requests: forward exactly what the backend returned.
      const request: ChatRequest = {
        user_query: userQuery,
        institution_id: DEMO_INSTITUTION_ID,
        session_id: sessionId,
        conversation_id: conversationId,
      }

      try {
        const response = await chat(request, accessToken)
        // The backend owns id creation; store and replay its values verbatim.
        setSessionId(response.session_id)
        setConversationId(response.conversation_id)
        setMessages((previous) => [
          ...previous,
          assistantMessageFrom(response),
        ])
      } catch (caught) {
        setError(chatErrorMessage(caught))
      } finally {
        setIsLoading(false)
      }
    },
    [accessToken, conversationId, isLoading, sessionId],
  )

  const resetChat = useCallback((): void => {
    // Local-only reset: the backend session/conversation rows are untouched and
    // no endpoint is called. The next message starts a fresh backend context by
    // omitting both identifiers.
    setMessages([])
    setSessionId(null)
    setConversationId(null)
    setError(null)
    setIsLoading(false)
  }, [])

  const loadConversation = useCallback(
    (conversationId: string, messages: MessageSummary[]): void => {
      // Map persisted messages into the existing ChatMessage representation.
      // Only user and assistant messages are expected from the backend.
      const mapped: ChatMessage[] = messages.map((msg) => ({
        id: nextUiMessageId(),
        role: msg.message_type === 'assistant' ? 'assistant' : 'user',
        content: msg.content_text,
      }))
      setMessages(mapped)
      // Set conversation ID so the next message continues in this conversation.
      // Session ID is intentionally NOT set: the history API doesn't return it,
      // and the backend uses conversation_id for lookup (chat.py line 224).
      setConversationId(conversationId)
      setSessionId(null)
      setError(null)
      setIsLoading(false)
    },
    [],
  )

  return {
    messages,
    isLoading,
    error,
    sessionId,
    conversationId,
    sendMessage,
    resetChat,
    loadConversation,
  }
}
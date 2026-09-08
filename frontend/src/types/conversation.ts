/**
 * Phase 5.7 — Conversation history contract types.
 *
 * Typed mirror of the Phase 5.6 conversation history API boundary:
 *     GET /api/v1/conversations
 *     GET /api/v1/conversations/{conversation_id}/messages
 *
 * These types mirror the locked backend Pydantic response schemas verbatim
 * (snake_case JSON names, UUIDs represented as strings at the HTTP boundary,
 * datetimes as ISO 8601 strings). The backend is authoritative:
 *     backend/app/schemas/conversation.py (ConversationSummary, MessageSummary)
 *
 * Only fields the backend actually returns are declared. `user_id` is
 * intentionally excluded: the history API never exposes it, and the frontend
 * must not expect it.
 */

/**
 * One conversation in the authenticated user's conversation list.
 *
 * Mirrors backend `ConversationSummary` (backend/app/schemas/conversation.py).
 * Conversations are ordered by `updated_at` DESC by the backend.
 */
export interface ConversationSummary {
  conversation_id: string
  title: string | null
  status: string
  created_at: string
  updated_at: string
}

/**
 * One persisted message returned by the conversation history API.
 *
 * Mirrors backend `MessageSummary` (backend/app/schemas/conversation.py).
 * Messages are ordered by `message_sequence` ASC by the backend.
 */
export interface MessageSummary {
  message_id: string
  conversation_id: string
  message_sequence: number
  message_type: string
  content_text: string
  created_at: string
}

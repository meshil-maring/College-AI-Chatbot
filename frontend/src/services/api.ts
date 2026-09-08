/**
 * Phase 5.3/5.7 — Typed API client for the locked backend chat and conversation
 * history endpoints.
 *
 * Uses the browser-native `fetch` API. No HTTP library is installed.
 * This module is only an HTTP boundary — it contains no retrieval,
 * generation, conversation, or authentication logic.
 *
 * Base URL comes from the Phase 5.2 environment strategy
 * (`VITE_API_BASE_URL=/api`). During development the Vite proxy forwards
 * `/api` to the FastAPI backend, so the client targets
 * `/api/v1/generation/chat` and `/api/v1/conversations` without hard-coding
 * a host.
 */

import type { ChatRequest, ChatResponse } from '../types/chat.ts'
import type {
  ConversationSummary,
  MessageSummary,
} from '../types/conversation.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

const CHAT_ENDPOINT: string = `${API_BASE_URL}/v1/generation/chat`
const CONVERSATIONS_ENDPOINT: string = `${API_BASE_URL}/v1/conversations`

/**
 * Error raised for a non-2xx HTTP response from the API.
 *
 * `status` is the HTTP status code, `details` is the parsed response body
 * when it was JSON (e.g. FastAPI's `{ "detail": ... }` payload).
 */
export class ApiError extends Error {
  readonly status: number
  readonly details: unknown

  constructor(status: number, message: string, details: unknown = undefined) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

/**
 * Best-effort parse of an error response body.
 * Returns `undefined` when the body is not JSON or cannot be parsed.
 */
async function readErrorDetails(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    return undefined
  }
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

/**
 * Build a human-readable message from an error response body.
 * Falls back to a generic message including the HTTP status.
 */
function formatApiErrorMessage(status: number, details: unknown): string {
  if (typeof details === 'object' && details !== null) {
    const detail = (details as Record<string, unknown>).detail
    if (typeof detail === 'string' && detail.length > 0) {
      return detail
    }
  }
  return `Chat request failed with HTTP ${status}`
}

/**
 * Send one chat request to `POST /api/v1/generation/chat`.
 *
 * @param request     The serialized `ChatRequest` body.
 * @param accessToken An already-obtained JWT, sent only as
 *                    `Authorization: Bearer <token>`. Authentication itself
 *                    is out of scope for this phase.
 * @returns The typed `ChatResponse` for a successful (2xx) HTTP response.
 * @throws ApiError   For non-2xx HTTP responses. HTTP failures are never
 *                    hidden behind a fabricated `ChatResponse`.
 */
export async function chat(
  request: ChatRequest,
  accessToken: string,
): Promise<ChatResponse> {
  const response = await fetch(CHAT_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const details = await readErrorDetails(response)
    throw new ApiError(
      response.status,
      formatApiErrorMessage(response.status, details),
      details,
    )
  }

  return (await response.json()) as ChatResponse
}

/**
 * List all conversations for the authenticated user.
 *
 * Calls `GET /api/v1/conversations` with the bearer token.
 * Conversations are ordered by `updated_at` DESC by the backend.
 *
 * @param accessToken An already-obtained JWT, sent only as
 *                    `Authorization: Bearer <token>`.
 * @returns The typed list of conversation summaries.
 * @throws ApiError For non-2xx HTTP responses.
 */
export async function listConversations(
  accessToken: string,
): Promise<ConversationSummary[]> {
  const response = await fetch(CONVERSATIONS_ENDPOINT, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  if (!response.ok) {
    const details = await readErrorDetails(response)
    throw new ApiError(
      response.status,
      formatApiErrorMessage(response.status, details),
      details,
    )
  }

  return (await response.json()) as ConversationSummary[]
}

/**
 * Retrieve persisted messages for one conversation.
 *
 * Calls `GET /api/v1/conversations/{conversation_id}/messages` with the
 * bearer token. Messages are ordered by `message_sequence` ASC by the backend.
 * Ownership is verified by the backend: a conversation that does not exist
 * or does not belong to the authenticated user produces a 404.
 *
 * @param conversationId The conversation whose messages to retrieve.
 * @param accessToken    An already-obtained JWT, sent only as
 *                       `Authorization: Bearer <token>`.
 * @returns The typed list of message summaries.
 * @throws ApiError For non-2xx HTTP responses, including 404
 *                   (CONVERSATION_NOT_FOUND) when the conversation is
 *                   unavailable or unauthorized.
 */
export async function getConversationMessages(
  conversationId: string,
  accessToken: string,
): Promise<MessageSummary[]> {
  const response = await fetch(
    `${CONVERSATIONS_ENDPOINT}/${conversationId}/messages`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  )

  if (!response.ok) {
    const details = await readErrorDetails(response)
    throw new ApiError(
      response.status,
      formatApiErrorMessage(response.status, details),
      details,
    )
  }

  return (await response.json()) as MessageSummary[]
}
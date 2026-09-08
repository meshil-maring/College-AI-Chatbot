/**
 * Phase 5.3 — Locked backend chat contract types.
 *
 * Typed representation of the Phase 4.4 HTTP boundary served by:
 *     POST /api/v1/generation/chat
 *
 * These types mirror the locked backend Pydantic schemas verbatim
 * (snake_case JSON names, UUIDs represented as strings at the HTTP
 * boundary). The backend is authoritative:
 *     backend/app/schemas/generation.py
 *     backend/app/schemas/chat.py
 *     backend/app/schemas/chat_response.py
 */

/** Valid response status values validated by the backend (do not broaden). */
export type ChatStatus = 'success' | 'insufficient_context'

/**
 * Public request accepted by POST /api/v1/generation/chat.
 *
 * Mirrors backend `ChatRequest` (backend/app/schemas/chat.py).
 * `retrieved_chunks` is an internal/backend concern and is intentionally
 * not exposed by the frontend.
 */
export interface ChatRequest {
  user_query: string
  session_id?: string | null
  conversation_id?: string | null
  institution_id: string
  knowledge_source_id?: string | null
  document_id?: string | null
  document_version_id?: string | null
  processing_run_id?: string | null
  model_name?: string | null
}

/**
 * Citation/grounding reference for answer content.
 *
 * Mirrors backend `SourceReference` (backend/app/schemas/generation.py).
 */
export interface SourceReference {
  chunk_id: string
  document_id?: string | null
  document_version_id?: string | null
  quote: string
  similarity_score?: number | null
}

/**
 * Frontend-friendly citation derived from a source reference.
 *
 * Mirrors backend `StructuredSource` (backend/app/schemas/chat_response.py).
 */
export interface StructuredSource {
  chunk_id: string
  quote: string
  relevance_score?: number | null
  source_title?: string | null
  section?: string | null
}

/**
 * Structured token usage information.
 *
 * Mirrors backend `ChatUsage` (backend/app/schemas/chat_response.py).
 */
export interface ChatUsage {
  input_tokens?: number | null
  output_tokens?: number | null
}

/**
 * Full response returned by POST /api/v1/generation/chat.
 *
 * Mirrors backend `ChatResponse` (backend/app/schemas/chat.py), which
 * extends `AIResponse` (backend/app/schemas/generation.py) — including the
 * inherited `source_references` and `metadata` fields that are part of the
 * serialized response.
 */
export interface ChatResponse {
  answer: string | null
  source_references: SourceReference[]
  status: ChatStatus
  model_used: string | null
  metadata: Record<string, unknown>
  session_id: string
  conversation_id: string
  message_id: string | null
  sources: StructuredSource[]
  usage: ChatUsage | null
}
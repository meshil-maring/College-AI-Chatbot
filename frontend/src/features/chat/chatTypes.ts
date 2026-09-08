/**
 * Phase 5.5 — Presentation-oriented chat message model.
 *
 * This type exists only so the React UI can render one history entry. It is
 * deliberately NOT a mirror of the backend database message model and carries
 * no business logic (no retrieval, generation, citation, or session rules).
 *
 * For assistant messages it simply carries the backend-provided answer plus
 * the backend-provided response metadata the UI may display:
 *   - status             ('success' | 'insufficient_context')
 *   - sources            (backend StructuredSource[] for citation cards)
 *   - sourceReferences   (backend SourceReference[], preserved verbatim)
 *   - usage              (backend token counts, only when provided)
 *   - modelUsed          (backend-selected model identifier)
 */

import type {
  ChatStatus,
  ChatUsage,
  SourceReference,
  StructuredSource,
} from '../../types/chat.ts'

export interface ChatMessage {
  /** Frontend-only key used to render React list items. */
  readonly id: string
  readonly role: 'user' | 'assistant'
  /** Plain text. For assistant messages this is the backend `answer`. */
  readonly content: string
  /** Backend response status; only present on assistant messages. */
  readonly status?: ChatStatus
  /** Backend structured sources rendered as citation cards. */
  readonly sources?: StructuredSource[]
  /** Backend source references preserved verbatim (not re-generated). */
  readonly sourceReferences?: SourceReference[]
  /** Backend token usage when the provider reported it. */
  readonly usage?: ChatUsage | null
  /** Backend model identifier when the provider reported it. */
  readonly modelUsed?: string | null
}
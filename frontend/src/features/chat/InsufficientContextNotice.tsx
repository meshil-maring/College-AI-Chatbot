/**
 * Phase 5.5 — Insufficient-context notice.
 *
 * Rendered when the backend returns status="insufficient_context" with no
 * answer. The frontend never fabricates an answer, never calls the LLM again,
 * and never hides the status. The wording is user-friendly but honest.
 */

export default function InsufficientContextNotice() {
  return (
    <div
      role="status"
      className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200"
    >
      <span className="font-semibold">Insufficient context:</span>{' '}
      I couldn't find enough information in the college knowledge base to answer
      that question reliably.
    </div>
  )
}
/**
 * Phase 5.5 — Loading indicator.
 *
 * Plain text + a small pulsing dot. No fake streaming, no token-by-token
 * generation: the backend endpoint returns a normal HTTP response, so the UI
 * simply shows that the chatbot is processing.
 */

export default function LoadingIndicator() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-2 text-sm text-slate-300"
    >
      <span
        className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"
        aria-hidden="true"
      />
      <span>Thinking…</span>
    </div>
  )
}
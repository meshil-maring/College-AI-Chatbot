import type { RecoveryState } from './useTurnRecovery.ts'

export default function RecoveryNotice({
  recovery,
  onCheck,
  onRetry,
  busy,
}: {
  recovery: RecoveryState | null
  onCheck: () => void
  onRetry: () => void
  busy: boolean
}) {
  if (!recovery) return null
  return (
    <section
      className="mx-4 mt-3 rounded-lg border border-control bg-surface p-3 text-sm text-content"
      aria-label="Reply recovery"
    >
      <p role="status">{recovery.message}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-lg border border-control bg-surface px-3 py-2 font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
          disabled={busy || recovery.checking}
          onClick={onCheck}
        >
          {recovery.checking ? 'Checking reply…' : 'Check reply'}
        </button>
        {recovery.retryable && recovery.request && (
          <button type="button" className="ui-primary" disabled={busy || recovery.checking} onClick={onRetry}>
            Retry reply
          </button>
        )}
      </div>
    </section>
  )
}

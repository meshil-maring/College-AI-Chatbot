export default function PublicRequestFeedback({
  loading,
  error,
  canRetry,
  retryAfterSeconds,
  onRetry,
  onStop,
}: {
  loading: boolean
  error: string | null
  canRetry: boolean
  retryAfterSeconds: number
  onRetry: () => void
  onStop: () => void
}) {
  return (
    <>
      {loading && (
        <div className="mt-5 mr-auto flex w-fit flex-wrap items-center gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-sm text-muted">
          <span role="status">Thinking…</span>
          <button
            type="button"
            onClick={onStop}
            className="rounded-lg border border-control px-3 py-2 text-xs font-semibold text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
          >
            Stop waiting
          </button>
        </div>
      )}
      {error && (
        <div className="mt-5 rounded-xl border border-danger bg-danger-bg p-3 text-sm text-danger">
          <p role="alert">{error}</p>
          {canRetry && (
            <button
              type="button"
              onClick={onRetry}
              disabled={loading || retryAfterSeconds > 0}
              className="mt-2 rounded-lg border border-control bg-surface px-3 py-2 text-xs font-semibold text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {retryAfterSeconds > 0 ? `Retry in ${retryAfterSeconds}s` : 'Retry'}
            </button>
          )}
        </div>
      )}
    </>
  )
}

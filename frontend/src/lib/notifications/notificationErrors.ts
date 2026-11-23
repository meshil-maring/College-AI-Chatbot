/**
 * Turns a failed request into user-safe toast text.
 *
 * API clients in `services/` throw domain error classes that carry an HTTP
 * `status`. Client errors (4xx) carry messages written for users — validation
 * and conflict explanations already shown inline today. Server errors, network
 * failures and unknown values may carry internal details, so they get a fixed
 * generic sentence instead.
 */

export const GENERIC_FAILURE_DESCRIPTION = 'Please try again. If the problem continues, contact your administrator.'

function statusOf(error: unknown): number | null {
  if (typeof error !== 'object' || error === null) return null
  const status = (error as { status?: unknown }).status
  return typeof status === 'number' ? status : null
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

/**
 * True when no toast should be shown at all: cancelled requests, and 401s,
 * which the session-expiry boundary already reports once for the whole app.
 */
export function isSilentFailure(error: unknown): boolean {
  return isAbortError(error) || statusOf(error) === 401
}

/** A description that is safe to display for a failed request. */
export function describeFailure(error: unknown): string {
  const status = statusOf(error)
  if (status !== null && status >= 400 && status < 500 && error instanceof Error) {
    const message = error.message.trim()
    if (message.length > 0 && message.length <= 300) return message
  }
  return GENERIC_FAILURE_DESCRIPTION
}

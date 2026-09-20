/**
 * Phase 6.15.4 — session-expiry event bus.
 *
 * A dependency-free publish/subscribe seam that lets ANY authenticated API
 * client report "the backend rejected this request with 401" to the
 * authentication boundary WITHOUT importing it (no api-client ↔ AuthProvider
 * ↔ auth-service circular dependency).
 *
 * Design notes:
 * - Only the AuthProvider subscribes; API clients publish. One global 401
 *   handling point instead of per-feature handling.
 * - Only an AUTHENTICATED request can raise `session_expired` — login
 *   failures are classified by the auth service (`invalid_credentials`) and
 *   never published here, so bad credentials can never clear or reset
 *   authentication state.
 * - The message is a fixed, user-safe string; backend error text is never
 *   surfaced.
 *
 * Phase 6.15.7 — the notification NAMES the token the failed request carried:
 *   * every API client passes the access token it sent, so the subscriber can
 *     tell a genuinely current session from a stale response (request A 401s
 *     while the user has already signed in again and now holds a newer token);
 *   * a notification for a token the provider no longer holds is ignored, so a
 *     stale 401 can never clear a freshly established session;
 *   * a caller that cannot name the token passes nothing (`null`), which is
 *     treated as "the current session" — the pre-6.15.7 behavior.
 */

export const SESSION_EXPIRED_MESSAGE: string =
  'Your session has expired. Please log in again.'

/** Receives the token whose request was rejected (null when unknown). */
type SessionExpiredListener = (accessToken: string | null) => void

let listeners: SessionExpiredListener[] = []

/** Subscribe to session-expiry notifications. Returns an unsubscribe fn. */
export function onSessionExpired(listener: SessionExpiredListener): () => void {
  listeners.push(listener)
  return () => {
    listeners = listeners.filter((registered) => registered !== listener)
  }
}

/**
 * Report that an authenticated API request was rejected with 401
 * (e.g. TOKEN_EXPIRED / INVALID_TOKEN / USER_NOT_FOUND): the token is no
 * longer accepted, so the saved session must be cleared.
 *
 * @param accessToken The exact token the failed request sent. Pass it whenever
 *                    it is known (every API client in this codebase does) so a
 *                    late response from an already-replaced session cannot
 *                    clear the session that has replaced it.
 */
export function notifySessionExpired(accessToken: string | null = null): void {
  for (const listener of [...listeners]) {
    listener(accessToken)
  }
}

/** Test-only: drop every listener (no global state leaks between tests). */
export function resetSessionExpiredListeners(): void {
  listeners = []
}

/** localStorage key for the saved access token (opaque, never a password). */
export const ACCESS_TOKEN_STORAGE_KEY: string = 'college-ai-chatbot.access-token'

export const REFRESH_TOKEN_STORAGE_KEY: string = 'college-ai-chatbot.refresh-token'

export const SESSION_EXPIRY_STORAGE_KEY = 'college-ai-chatbot.session-expires-at'

export function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function readStoredRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function readStoredExpiry(): number | null {
  try {
    const raw = window.localStorage.getItem(SESSION_EXPIRY_STORAGE_KEY)
    const expiry = raw === null ? NaN : Number(raw)
    return Number.isFinite(expiry) ? expiry : null
  } catch {
    return null
  }
}

export function storeToken(token: string | null): void {
  try {
    if (token === null) {
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
    } else {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
    }
  } catch {
    // Storage unavailable (e.g. private browsing): the session stays in memory.
  }
}

export function storeProviderSession(accessToken: string, refreshToken: string, expiresIn: number): void {
  storeToken(accessToken)
  try {
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken)
    window.localStorage.setItem(SESSION_EXPIRY_STORAGE_KEY, String(Date.now() + Math.max(0, expiresIn) * 1000))
  } catch {
    // The in-memory session remains usable when browser storage is unavailable.
  }
}

export function clearStoredProviderSession(): void {
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
    window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
    window.localStorage.removeItem(SESSION_EXPIRY_STORAGE_KEY)
  } catch {
    // The in-memory session is still cleared when storage is unavailable.
  }
}

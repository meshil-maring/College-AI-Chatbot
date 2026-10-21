import { notifySessionExpired } from '../shared/sessionEvents.ts'

export const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export const PLATFORM_BASE = `${API_BASE_URL}/v1/platform/institutions`

/** A platform API failure carrying the server's stable error code. */
export class PlatformInstitutionError extends Error {
  readonly status: number
  readonly code: string | null

  constructor(status: number, message: string, code: string | null = null) {
    super(message)
    this.name = 'PlatformInstitutionError'
    this.status = status
    this.code = code
  }
}

/** Extract the `{ error: { code, message } }` envelope used by AppError. */
export async function readError(response: Response): Promise<{ message: string; code: string | null }> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null) {
      const envelope = (body as Record<string, unknown>).error
      if (typeof envelope === 'object' && envelope !== null) {
        const record = envelope as Record<string, unknown>
        const message = typeof record.message === 'string' ? record.message : null
        const code = typeof record.code === 'string' ? record.code : null
        if (message !== null) return { message, code }
        if (code !== null) return { message: `Request failed (${code})`, code }
      }
    }
  } catch {
    // Non-JSON error body; fall through to the status-based message.
  }
  return { message: `Request failed with HTTP ${response.status}`, code: null }
}

export async function requestJson<T>(
  method: 'GET' | 'POST' | 'PATCH',
  endpoint: string,
  accessToken: string,
  body?: unknown,
): Promise<T> {
  let response: Response
  try {
    const headers: Record<string, string> = { Authorization: `Bearer ${accessToken}` }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    response = await fetch(endpoint, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new PlatformInstitutionError(0, 'Could not reach the backend. Please try again.')
  }

  if (response.status === 401) notifySessionExpired(accessToken)
  if (!response.ok) {
    const { message, code } = await readError(response)
    throw new PlatformInstitutionError(response.status, message, code)
  }
  return (await response.json()) as T
}

import { API_BASE_URL } from './client.ts'

export interface StudentInvitationDetails {
  status: 'pending' | 'accepted'
  student_name: string
  email: string
  institution_name: string
  batch_name: string
  batch_code: string
  section_name: string
  section_active: boolean
  expires_at: string
}

export interface StudentInvitationCompletion {
  message: string
  completed: boolean
}

const BASE = `${API_BASE_URL}/v1/student-onboarding`

async function requestSetupJson<T>(endpoint: string, body: unknown, timeoutMs: number): Promise<T> {
  const controller = typeof AbortController === 'function' ? new AbortController() : null
  const timeoutId = controller === null ? null : setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller?.signal,
    })
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === 'AbortError') {
      throw new Error('Student account setup timed out. Please try again.')
    }
    throw new Error('Could not reach the server. Please try again.')
  } finally {
    if (timeoutId !== null) clearTimeout(timeoutId)
  }

  if (!response.ok) {
    let message =
      response.status >= 500
        ? 'Student account setup is temporarily unavailable. Please try again later.'
        : 'This setup link is invalid or unavailable. Contact your institution administrator.'
    if (response.headers.get('content-type')?.includes('application/json')) {
      try {
        const payload: unknown = await response.json()
        if (typeof payload === 'object' && payload !== null) {
          const error = (payload as Record<string, unknown>).error
          if (typeof error === 'object' && error !== null) {
            const detail = (error as Record<string, unknown>).message
            if (typeof detail === 'string' && detail.trim()) message = detail
          }
        }
      } catch {
        // Keep the safe status-based message when the server response is malformed.
      }
    }
    throw new Error(message)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new Error('The server returned an invalid response during student setup.')
  }
}

export function inspectStudentSetup(token: string): Promise<StudentInvitationDetails> {
  return requestSetupJson(`${BASE}/inspect`, { token }, 15_000)
}

export function completeStudentSetup(token: string, password: string): Promise<StudentInvitationCompletion> {
  return requestSetupJson(`${BASE}/complete`, { token, password }, 30_000)
}

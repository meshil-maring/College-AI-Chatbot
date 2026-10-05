const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export interface UniversityRegistrationRequest {
  name: string
  institution_code: string
  organization_code: string
  join_code?: string | null
  official_email: string
  location?: string | null
  admin_email: string
  admin_password: string
  admin_first_name: string
  admin_last_name: string
}

export interface UniversityRegistrationResponse {
  message: string
  institution_code: string
  status: string
  email: string
}

export class UniversityRegistrationError extends Error {
  readonly status: number | null
  readonly code: string | null

  constructor(message: string, status: number | null = null, code: string | null = null) {
    super(message)
    this.name = 'UniversityRegistrationError'
    this.status = status
    this.code = code
  }
}

function safeMessage(status: number, code: string | null): string {
  if (status === 409) {
    if (code === 'EMAIL_ALREADY_REGISTERED') return 'An account with this administrator email already exists.'
    return 'This university or account is already registered.'
  }
  if (status === 404) return 'The organization code was not found.'
  if (status === 403) return 'This organization is not accepting university registrations.'
  if (status === 422) return 'Please review the registration details and try again.'
  if (status >= 500) return 'The server could not complete registration. Please try again later.'
  return 'University registration could not be completed.'
}

export async function registerUniversity(
  request: UniversityRegistrationRequest,
): Promise<UniversityRegistrationResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/v1/institutions/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    throw new UniversityRegistrationError('Could not reach the backend. Please try again.')
  }

  const body = await response.json().catch(() => undefined) as
    | { error?: { code?: unknown } }
    | UniversityRegistrationResponse
    | undefined
  if (!response.ok) {
    const rawCode = body && 'error' in body ? body.error?.code : null
    const code = typeof rawCode === 'string' ? rawCode : null
    throw new UniversityRegistrationError(safeMessage(response.status, code), response.status, code)
  }
  return body as UniversityRegistrationResponse
}

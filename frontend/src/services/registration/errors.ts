/** Distinguishes why a registration/institution-lookup operation failed. */
export type RegistrationErrorKind =
  | 'institution_not_found' // 404 INSTITUTION_NOT_FOUND from /institutions/lookup
  | 'institution_not_accepting' // 403 INSTITUTION_NOT_ACCEPTING_REGISTRATIONS
  | 'email_already_registered' // 409 EMAIL_ALREADY_REGISTERED / STUDENT_ALREADY_REGISTERED
  | 'register_number_already_registered' // 409 REGISTER_NUMBER_ALREADY_REGISTERED
  | 'roll_number_already_registered' // 409 ROLL_NUMBER_ALREADY_REGISTERED
  | 'validation' // 422 VALIDATION_ERROR (client contract mismatch)
  | 'server' // 5xx upstream error
  | 'unavailable' // institution verification dependency unavailable
  | 'network' // request never produced an HTTP response
  | 'timeout' // request aborted via timeout signal
  | 'rate_limited'
  | 'unknown'

/** User-safe message for each failure kind (never contains internals). */
export function registrationErrorMessage(error: RegistrationError): string {
  switch (error.kind) {
    case 'institution_not_found':
      return 'Institution code was not found. Please check the code and try again.'
    case 'institution_not_accepting':
      return 'This institution is not currently accepting registrations.'
    case 'email_already_registered':
      return 'An account with this email already exists.'
    case 'register_number_already_registered':
      return 'This register number is already registered.'
    case 'roll_number_already_registered':
      return 'This university roll number is already registered.'
    case 'validation':
      return 'Please review the highlighted fields and try again.'
    case 'server':
      return 'The server reported an error. Please try again later.'
    case 'unavailable':
      return 'Institution verification is temporarily unavailable. Please try again shortly.'
    case 'network':
      return 'Could not reach the backend. Please make sure the server is running, then try again.'
    case 'timeout':
      return 'The request timed out. Please try again.'
    case 'rate_limited':
      return 'Too many registration requests. Please wait a moment and try again.'
    default:
      return 'Something went wrong. Please try again.'
  }
}

/**
 * Error raised for every failed registration/lookup operation.
 * `kind` is resolved from the backend `error.code` (never from parsing
 * arbitrary strings); `message` is always safe for end-user display.
 */
export class RegistrationError extends Error {
  readonly kind: RegistrationErrorKind
  /** HTTP status when a response was received, otherwise null (network). */
  readonly status: number | null
  /** Backend `error.code` when the AppError envelope was present. */
  readonly code: string | null

  constructor(kind: RegistrationErrorKind, status: number | null, code: string | null, message: string | null = null) {
    super(message ?? registrationErrorMessage({ kind } as RegistrationError))
    this.name = 'RegistrationError'
    this.kind = kind
    this.status = status
    this.code = code
  }
}

export function kindForCode(code: string | null): RegistrationErrorKind {
  switch (code) {
    case 'INSTITUTION_NOT_FOUND':
      return 'institution_not_found'
    case 'INSTITUTION_NOT_ACCEPTING_REGISTRATIONS':
      return 'institution_not_accepting'
    case 'EMAIL_ALREADY_REGISTERED':
    case 'STUDENT_ALREADY_REGISTERED':
      return 'email_already_registered'
    case 'REGISTER_NUMBER_ALREADY_REGISTERED':
      return 'register_number_already_registered'
    case 'ROLL_NUMBER_ALREADY_REGISTERED':
      return 'roll_number_already_registered'
    default:
      return 'unknown'
  }
}

export async function readJsonBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return undefined
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

export function extractCode(body: unknown): string | null {
  if (typeof body === 'object' && body !== null) {
    const error = (body as Record<string, unknown>).error
    if (typeof error === 'object' && error !== null) {
      const code = (error as Record<string, unknown>).code
      if (typeof code === 'string') return code
    }
  }
  return null
}

/** Classify a received HTTP error response into a user-safe RegistrationError. */
export async function buildRegistrationError(response: Response): Promise<RegistrationError> {
  const status = response.status
  const body = await readJsonBody(response)
  const code = extractCode(body)

  if (status === 429) {
    return new RegistrationError('rate_limited', status, code)
  }

  if (status === 422) {
    return new RegistrationError('validation', status, code ?? 'VALIDATION_ERROR')
  }
  if (status === 409) {
    const kind = kindForCode(code)
    return new RegistrationError(kind === 'unknown' ? 'email_already_registered' : kind, status, code)
  }
  if (status === 404) {
    const kind = kindForCode(code)
    return new RegistrationError(kind === 'unknown' ? 'institution_not_found' : kind, status, code)
  }
  if (status === 403) {
    const kind = kindForCode(code)
    return new RegistrationError(kind === 'unknown' ? 'institution_not_accepting' : kind, status, code)
  }
  if (status >= 500) {
    return new RegistrationError(code === 'INSTITUTION_LOOKUP_UNAVAILABLE' ? 'unavailable' : 'server', status, code)
  }
  return new RegistrationError('unknown', status, code)
}

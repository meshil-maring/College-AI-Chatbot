/**
 * Phase 6.15.2 — Registration & institution-lookup service client.
 *
 * Talks exclusively to the existing public backend endpoints:
 *     GET  /api/v1/institutions/lookup   (resolve a public institution code)
 *     POST /api/v1/users/register        (Phase 6.13.5 unified registration;
 *                                         registration_type='student')
 *
 * Contract notes verified against the repository:
 * - `POST /api/v1/users/register` accepts `institution_code` (2–64 chars) and
 *   resolves it SERVER-SIDE to the institution id — the frontend never holds,
 *   trusts, or submits a user-supplied institution UUID.
 * - The created student always starts `approval_status='pending'`; the
 *   response contains NO token, so a successful registration is NEVER treated
 *   as an authenticated session.
 * - Error envelope: `{ "error": { "code": "…", "message": "…" } }` (AppError);
 *   request-validation failures return 422 VALIDATION_ERROR.
 *
 * Boundaries mirror `services/auth.ts`: no credential handling, nothing
 * logged, user-safe messages only. The password is sent only in the POST
 * body to the backend (which forwards it solely to Supabase Auth GoTrue).
 */

import type {
  InstitutionLookupResponse,
  RegistrationRequest,
  RegistrationResponse,
} from '../types/registration.ts'

const API_BASE_URL: string = (
  import.meta.env?.VITE_API_BASE_URL ?? '/api'
).replace(/\/+$/, '')

const LOOKUP_ENDPOINT: string = `${API_BASE_URL}/v1/institutions/lookup`
const REGISTER_ENDPOINT: string = `${API_BASE_URL}/v1/users/register`

/** Distinguishes why a registration/institution-lookup operation failed. */
export type RegistrationErrorKind =
  | 'institution_not_found' // 404 INSTITUTION_NOT_FOUND from /institutions/lookup
  | 'institution_not_accepting' // 403 INSTITUTION_NOT_ACCEPTING_REGISTRATIONS
  | 'email_already_registered' // 409 EMAIL_ALREADY_REGISTERED / STUDENT_ALREADY_REGISTERED
  | 'register_number_already_registered' // 409 REGISTER_NUMBER_ALREADY_REGISTERED
  | 'roll_number_already_registered' // 409 ROLL_NUMBER_ALREADY_REGISTERED
  | 'validation' // 422 VALIDATION_ERROR (client contract mismatch)
  | 'server' // 5xx upstream error
  | 'network' // request never produced an HTTP response
  | 'timeout' // request aborted via timeout signal
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
    case 'network':
      return 'Could not reach the backend. Please make sure the server is running, then try again.'
    case 'timeout':
      return 'The request timed out. Please try again.'
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

  constructor(
    kind: RegistrationErrorKind,
    status: number | null,
    code: string | null,
    message: string | null = null,
  ) {
    super(message ?? registrationErrorMessage({ kind } as RegistrationError))
    this.name = 'RegistrationError'
    this.kind = kind
    this.status = status
    this.code = code
  }
}

function kindForCode(code: string | null): RegistrationErrorKind {
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

async function readJsonBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) return undefined
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

function extractCode(body: unknown): string | null {
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
async function buildRegistrationError(
  response: Response,
): Promise<RegistrationError> {
  const status = response.status
  const body = await readJsonBody(response)
  const code = extractCode(body)

  if (status === 422) {
    return new RegistrationError('validation', status, code ?? 'VALIDATION_ERROR')
  }
  if (status === 409) {
    const kind = kindForCode(code)
    return new RegistrationError(
      kind === 'unknown' ? 'email_already_registered' : kind,
      status,
      code,
    )
  }
  if (status === 404) {
    const kind = kindForCode(code)
    return new RegistrationError(
      kind === 'unknown' ? 'institution_not_found' : kind,
      status,
      code,
    )
  }
  if (status === 403) {
    const kind = kindForCode(code)
    return new RegistrationError(
      kind === 'unknown' ? 'institution_not_accepting' : kind,
      status,
      code,
    )
  }
  if (status >= 500) {
    return new RegistrationError('server', status, code)
  }
  return new RegistrationError('unknown', status, code)
}

/**
 * Shared JSON fetch helper.
 *
 * - `timeoutMs > 0` aborts the request after the given delay (kind `timeout`).
 * - fetch-level rejection (DNS, refused, CORS, aborted) maps to a kind:
 *   the timeout `AbortError` becomes `timeout`; everything else `network`.
 * - Non-2xx responses are classified into user-safe `RegistrationError`s.
 */
async function requestJson<T>(
  method: 'GET' | 'POST',
  endpoint: string,
  body: unknown,
  timeoutMs: number,
): Promise<T> {
  const controller =
    timeoutMs > 0 && typeof AbortController === 'function'
      ? new AbortController()
      : null
  const timeoutId =
    controller !== null ? setTimeout(() => controller.abort(), timeoutMs) : null

  let response: Response
  try {
    response = await fetch(endpoint, {
      method,
      headers:
        body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller?.signal,
    })
  } catch (err) {
    if (
      err instanceof DOMException &&
      err.name === 'AbortError' &&
      controller !== null
    ) {
      throw new RegistrationError('timeout', null, null)
    }
    throw new RegistrationError('network', null, null)
  } finally {
    if (timeoutId !== null) clearTimeout(timeoutId)
  }

  if (!response.ok) {
    throw await buildRegistrationError(response)
  }
  return (await response.json()) as T
}

/**
 * Resolve a public institution code to its safe public identity.
 *
 * @param code The institution code as typed by the student (case-insensitive;
 *             the backend normalizes it).
 * @returns `{ institution_id, code, name }` — the ONLY fields the backend
 *          exposes. Registration itself re-resolves the code server-side, so
 *          the returned id is display context only.
 * @throws RegistrationError `institution_not_found` (404),
 *          `institution_not_accepting` (403), `validation` (422),
 *          `network` / `timeout` / `server` / `unknown`.
 */
export async function lookupInstitution(
  code: string,
  timeoutMs: number = 10_000,
): Promise<InstitutionLookupResponse> {
  return requestJson<InstitutionLookupResponse>(
    'GET',
    `${LOOKUP_ENDPOINT}?code=${encodeURIComponent(code)}`,
    undefined,
    timeoutMs,
  )
}

/**
 * Submit the student registration to POST /api/v1/users/register.
 *
 * @param request `{ registration_type: 'student', institution_code, email,
 *                  password, first_name, last_name, register_number?,
 *                  university_roll_number? }` — exactly the backend schema.
 * @returns The typed registration response (`approval_status: 'pending'`,
 *          no token). The caller must NEVER treat this as a login.
 * @throws RegistrationError Classified per `RegistrationErrorKind`, including
 *          the duplicate-identity kinds (409) and `validation` (422).
 */
export async function registerStudent(
  request: RegistrationRequest,
  timeoutMs: number = 20_000,
): Promise<RegistrationResponse> {
  return requestJson<RegistrationResponse>(
    'POST',
    REGISTER_ENDPOINT,
    request,
    timeoutMs,
  )
}

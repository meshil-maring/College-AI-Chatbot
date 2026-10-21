import type { InstitutionLookupResponse, RegistrationRequest, RegistrationResponse } from '../../types/registration.ts'
import { RegistrationError, buildRegistrationError } from './errors.ts'
export const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export const LOOKUP_ENDPOINT: string = `${API_BASE_URL}/v1/institutions/lookup`

export const REGISTER_ENDPOINT: string = `${API_BASE_URL}/v1/users/register`

/**
 * Shared JSON fetch helper.
 *
 * - `timeoutMs > 0` aborts the request after the given delay (kind `timeout`).
 * - fetch-level rejection (DNS, refused, CORS, aborted) maps to a kind:
 *   the timeout `AbortError` becomes `timeout`; everything else `network`.
 * - Non-2xx responses are classified into user-safe `RegistrationError`s.
 */
export async function requestJson<T>(
  method: 'GET' | 'POST',
  endpoint: string,
  body: unknown,
  timeoutMs: number,
): Promise<T> {
  const controller = timeoutMs > 0 && typeof AbortController === 'function' ? new AbortController() : null
  const timeoutId = controller !== null ? setTimeout(() => controller.abort(), timeoutMs) : null

  let response: Response
  try {
    response = await fetch(endpoint, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller?.signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError' && controller !== null) {
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
export async function lookupInstitution(code: string, timeoutMs: number = 10_000): Promise<InstitutionLookupResponse> {
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
  return requestJson<RegistrationResponse>('POST', REGISTER_ENDPOINT, request, timeoutMs)
}

/** Submit a faculty registration request. The account remains pending. */
export async function registerFaculty(
  request: RegistrationRequest,
  timeoutMs: number = 20_000,
): Promise<RegistrationResponse> {
  return requestJson<RegistrationResponse>('POST', REGISTER_ENDPOINT, request, timeoutMs)
}

/** Submit a staff registration request. The account remains pending. */
export async function registerStaff(
  request: RegistrationRequest,
  timeoutMs: number = 20_000,
): Promise<RegistrationResponse> {
  return requestJson<RegistrationResponse>('POST', REGISTER_ENDPOINT, request, timeoutMs)
}

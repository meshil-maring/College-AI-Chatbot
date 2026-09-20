/**
 * Phase 6.15.2 — Registration & institution-lookup contract types.
 *
 * Typed mirrors of the actual backend boundary, verified against:
 *     GET  /api/v1/institutions/lookup   (backend/app/api/institutions.py)
 *     POST /api/v1/users/register        (backend/app/api/users.py)
 *
 * The backend is authoritative:
 *     backend/app/schemas/tenancy.py    (InstitutionLookupResponse — SAFE
 *                                        public projection: id/code/name only)
 *     backend/app/schemas/users.py      (UserRegistrationRequest/Response)
 *     backend/app/core/errors.py        (AppError `{error:{code,message}}`)
 *
 * Design invariant (backend-enforced): the public registration payload never
 * accepts internal database ids — it carries the public `institution_code`,
 * which the SERVER resolves to the institution id. The frontend therefore
 * never holds a user-supplied institution UUID at all.
 *
 * Error responses use the backend `AppError` envelope:
 *     { "error": { "code": "…", "message": "…" } }
 * with HTTP 404 (INSTITUTION_NOT_FOUND), 403
 * (INSTITUTION_NOT_ACCEPTING_REGISTRATIONS), 409 (EMAIL_ALREADY_REGISTERED,
 * STUDENT_ALREADY_REGISTERED, REGISTER_NUMBER_ALREADY_REGISTERED,
 * ROLL_NUMBER_ALREADY_REGISTERED), and 422 (VALIDATION_ERROR,
 * IDENTIFIER_REQUIRED — the framework-level handler normalizes 422s).
 */

/** Response of GET /api/v1/institutions/lookup (SAFE public projection). */
export interface InstitutionLookupResponse {
  institution_id: string
  code: string
  name: string
}

/** Student-specific fields of the registration payload. */
export type RegistrationType = 'student'

/** Request body accepted by POST /api/v1/users/register (registration_type='student'). */
export interface RegistrationRequest {
  registration_type: RegistrationType
  /** Public institution code (2–64 chars); resolved SERVER-SIDE. */
  institution_code: string
  email: string
  /** Sent only to the backend, which forwards it solely to Supabase Auth. */
  password: string
  first_name: string
  last_name: string
  /** Optional; at least one of register_number / university_roll_number is required. */
  register_number?: string | null
  university_roll_number?: string | null
}

/** Response returned by POST /api/v1/users/register (mirrors backend UserRegistrationResponse). */
export interface RegistrationResponse {
  message: string
  user_id: string
  institution_id: string
  institution_code: string
  registration_type: string
  /** Always 'pending' for self-registration; approval is a separate admin workflow. */
  approval_status: string
  student_id: string | null
  request_id: string | null
}

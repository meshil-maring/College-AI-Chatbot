import type { RegistrationType } from '../../../types/registration.ts'

/**
 * Public self-registration URLs. Each account type has its own route:
 * `/signup/student`, `/signup/faculty` and `/signup/staff`.
 *
 * The path only selects which form is shown. It is never sent as a role
 * claim: each form calls its own registration endpoint, and the server creates
 * a pending account whose role and approval state it decides itself.
 */
export const SIGNUP_TYPES: readonly RegistrationType[] = ['student', 'faculty', 'staff']

export function isSignupType(value: string | undefined | null): value is RegistrationType {
  return SIGNUP_TYPES.includes(value as RegistrationType)
}

function withInstitution(path: string, institutionCode?: string | null): string {
  const code = institutionCode?.trim()
  return code ? `${path}?institution=${encodeURIComponent(code)}` : path
}

/** Registration page for one account type, optionally pre-filling the institution code. */
export function signupPath(type: RegistrationType, institutionCode?: string | null): string {
  return withInstitution(`/signup/${type}`, institutionCode)
}

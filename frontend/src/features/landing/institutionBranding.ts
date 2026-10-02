import type { InstitutionLookupResponse } from '../../types/registration.ts'

/**
 * Frontend boundary for future institution-managed branding. The current safe
 * public lookup supplies only name/code/id, so all other values use neutral
 * local defaults rather than invented persistent data.
 */
export interface InstitutionBranding {
  readonly name: string
  readonly logo: string | null
  readonly primary_color: string
  readonly secondary_color: string
  readonly welcome_message: string
}

export const DEFAULT_INSTITUTION_BRANDING: InstitutionBranding = {
  name: 'Your university',
  logo: null,
  primary_color: '#059669',
  secondary_color: '#0f172a',
  welcome_message: 'Explore public university information or sign in for personalized access.',
}

export function createInstitutionBranding(
  institution: Pick<InstitutionLookupResponse, 'name'>,
): InstitutionBranding {
  return {
    ...DEFAULT_INSTITUTION_BRANDING,
    name: institution.name,
    welcome_message: `Welcome to ${institution.name}. Explore public information or sign in for personalized access.`,
  }
}


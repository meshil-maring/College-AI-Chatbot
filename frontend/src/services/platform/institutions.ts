import type {
  InstitutionAdminAssignment,
  InstitutionCreateInput,
  InstitutionDetail,
  InstitutionLifecycleResult,
  InstitutionSummary,
  InstitutionUpdateInput,
} from '../../types/platform.ts'
import { PLATFORM_BASE, requestJson } from './http.ts'
/** List every institution with safe platform metadata. */
export async function listInstitutions(accessToken: string): Promise<InstitutionSummary[]> {
  const body = await requestJson<{ institutions: InstitutionSummary[] }>('GET', PLATFORM_BASE, accessToken)
  return body.institutions
}

/** Read one institution's safe configuration detail. */
export async function getInstitution(accessToken: string, institutionId: string): Promise<InstitutionDetail> {
  return requestJson<InstitutionDetail>('GET', `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}`, accessToken)
}

/** Create an institution. The code is normalized and validated server-side. */
export async function createInstitution(
  accessToken: string,
  input: InstitutionCreateInput,
): Promise<InstitutionDetail> {
  return requestJson<InstitutionDetail>('POST', PLATFORM_BASE, accessToken, input)
}

/** Update an institution's safe configuration (never its lifecycle status). */
export async function updateInstitution(
  accessToken: string,
  institutionId: string,
  input: InstitutionUpdateInput,
): Promise<InstitutionDetail> {
  return requestJson<InstitutionDetail>(
    'PATCH',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}`,
    accessToken,
    input,
  )
}

/**
 * Suspend an institution. Existing data is retained and no accounts are
 * revoked — the server's returned message states this explicitly.
 */
export async function suspendInstitution(
  accessToken: string,
  institutionId: string,
): Promise<InstitutionLifecycleResult> {
  return requestJson<InstitutionLifecycleResult>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/suspend`,
    accessToken,
  )
}

/** Activate a pending institution or reactivate a suspended institution. */
export async function activateInstitution(
  accessToken: string,
  institutionId: string,
): Promise<InstitutionLifecycleResult> {
  return requestJson<InstitutionLifecycleResult>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/activate`,
    accessToken,
  )
}

/**
 * Assign an EXISTING account as University Admin of one institution.
 *
 * This is an assignment, not provisioning: no password is sent and no Auth
 * account is created. The granted role is fixed server-side to the
 * institution-scoped `admin` role.
 */
export async function assignInstitutionAdmin(
  accessToken: string,
  institutionId: string,
  email: string,
): Promise<InstitutionAdminAssignment> {
  return requestJson<InstitutionAdminAssignment>(
    'POST',
    `${PLATFORM_BASE}/${encodeURIComponent(institutionId)}/admins`,
    accessToken,
    { email },
  )
}

/** Minimal Phase 7.12 client for the server-authoritative platform boundary. */

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const PLATFORM_ME_ENDPOINT = `${API_BASE_URL}/v1/platform/me`

export interface PlatformIdentity {
  role: 'super_admin'
  scope: 'platform'
}

export class PlatformAuthorizationError extends Error {
  readonly status: number

  constructor(status: number) {
    super(status === 403 ? 'Platform access is not authorized.' : 'Platform access could not be verified.')
    this.name = 'PlatformAuthorizationError'
    this.status = status
  }
}

export async function getPlatformIdentity(accessToken: string): Promise<PlatformIdentity> {
  let response: Response
  try {
    response = await fetch(PLATFORM_ME_ENDPOINT, {
      method: 'GET',
      headers: { Authorization: `Bearer ${accessToken}` },
    })
  } catch {
    throw new PlatformAuthorizationError(0)
  }
  if (!response.ok) throw new PlatformAuthorizationError(response.status)
  const body = await response.json() as Partial<PlatformIdentity>
  if (body.role !== 'super_admin' || body.scope !== 'platform') {
    throw new PlatformAuthorizationError(500)
  }
  return body as PlatformIdentity
}


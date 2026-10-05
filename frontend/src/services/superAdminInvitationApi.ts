/**
 * Phase 9 — Super Admin invitation client.
 *
 * Authenticated calls (invite/list/cancel) send the session token only in the
 * Authorization header. Public calls (inspect/register) are authorized by the
 * opaque one-time token alone; the password is sent only on `register`.
 */

import { notifySessionExpired } from './sessionEvents.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const PLATFORM_BASE = `${API_BASE_URL}/v1/platform/super-admins/invitations`
const PUBLIC_BASE = `${API_BASE_URL}/v1/super-admin-invitations`

export interface SuperAdminInvitation {
  invitation_id: string
  email: string
  status: string
  expires_at: string | null
  created_at: string | null
}

export interface SuperAdminInviteCreated {
  invitation: SuperAdminInvitation
  invitation_token: string
  invitation_url: string
  expires_in_hours: number
}

export interface SuperAdminInvitePublicView {
  email: string
  status: string
  expires_at: string | null
}

export interface SuperAdminRegisterInput {
  password: string
  confirm_password: string
  first_name: string
  last_name: string
}

export interface SuperAdminRegistered {
  email: string
  role: string
  message: string
}

export class SuperAdminInvitationError extends Error {
  readonly status: number
  readonly code: string | null

  constructor(status: number, message: string, code: string | null = null) {
    super(message)
    this.name = 'SuperAdminInvitationError'
    this.status = status
    this.code = code
  }

  get isTerminal(): boolean {
    return (
      this.code === 'INVITATION_EXPIRED' ||
      this.code === 'INVITATION_CANCELLED' ||
      this.code === 'INVITATION_ALREADY_ACCEPTED'
    )
  }
}

async function readError(response: Response): Promise<{ message: string; code: string | null }> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null) {
      const envelope = (body as Record<string, unknown>).error
      if (typeof envelope === 'object' && envelope !== null) {
        const record = envelope as Record<string, unknown>
        const code = typeof record.code === 'string' ? record.code : null
        if (typeof record.message === 'string') return { message: record.message, code }
      }
    }
  } catch {
    // Non-JSON body.
  }
  return { message: `Request failed with HTTP ${response.status}`, code: null }
}

async function request<T>(
  method: 'GET' | 'POST',
  endpoint: string,
  options: { accessToken?: string; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.accessToken !== undefined) headers.Authorization = `Bearer ${options.accessToken}`
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  let response: Response
  try {
    response = await fetch(endpoint, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new SuperAdminInvitationError(0, 'Could not reach the backend. Please try again.')
  }
  if (response.status === 401 && options.accessToken !== undefined) {
    notifySessionExpired(options.accessToken)
  }
  if (!response.ok) {
    const { message, code } = await readError(response)
    throw new SuperAdminInvitationError(response.status, message, code)
  }
  return (await response.json()) as T
}

export async function createSuperAdminInvitation(
  accessToken: string,
  email: string,
): Promise<SuperAdminInviteCreated> {
  return request('POST', PLATFORM_BASE, { accessToken, body: { email } })
}

export async function listSuperAdminInvitations(
  accessToken: string,
): Promise<SuperAdminInvitation[]> {
  const result = await request<{ invitations: SuperAdminInvitation[] }>('GET', PLATFORM_BASE, {
    accessToken,
  })
  return result.invitations
}

export async function cancelSuperAdminInvitation(
  accessToken: string,
  invitationId: string,
): Promise<SuperAdminInvitation> {
  return request('POST', `${PLATFORM_BASE}/${encodeURIComponent(invitationId)}/cancel`, {
    accessToken,
  })
}

export async function inspectSuperAdminInvitation(
  token: string,
): Promise<SuperAdminInvitePublicView> {
  return request('GET', `${PUBLIC_BASE}/${encodeURIComponent(token)}`)
}

export async function registerSuperAdmin(
  token: string,
  input: SuperAdminRegisterInput,
): Promise<SuperAdminRegistered> {
  return request('POST', `${PUBLIC_BASE}/${encodeURIComponent(token)}/register`, { body: input })
}

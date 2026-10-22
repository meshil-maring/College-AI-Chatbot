import { notifySessionExpired } from '../shared/sessionEvents.ts'
import type {
  AcademicPackageCatalogue,
  AcademicPackageCommands,
  PackageOperation,
  PackageRecord,
} from '../../types/academicPackages.ts'

const BASE = `${(import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')}/v1/academic-packages`

async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  })
  if (response.status === 401) notifySessionExpired(token)
  const body = (await response.json().catch(() => null)) as { error?: { message?: string } } | null
  if (!response.ok) throw new Error(body?.error?.message ?? 'The academic package request could not be completed.')
  return body as T
}

export function getAcademicPackages(token: string, signal?: AbortSignal): Promise<AcademicPackageCatalogue> {
  return request(token, '', { signal })
}

export function commandAcademicPackage<K extends PackageOperation>(
  token: string,
  operation: K,
  payload: AcademicPackageCommands[K],
): Promise<PackageRecord> {
  return request(token, `/${operation}`, { method: 'POST', body: JSON.stringify(payload) })
}

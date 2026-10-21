import { useMemo } from 'react'
import { useAuth } from './AuthProvider.tsx'
import { createPermissions } from './rbac.ts'

/** React adapter for the current authenticated user's server-resolved grants. */
export function usePermissions() {
  const { status, user } = useAuth()
  const granted = status === 'authenticated' ? user?.effective_permissions : undefined
  return useMemo(() => createPermissions(granted), [granted])
}

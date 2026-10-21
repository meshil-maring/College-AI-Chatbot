import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePermissions } from './usePermissions.ts'

const auth = vi.hoisted(() => ({
  status: 'authenticated',
  user: { role: 'admin', effective_permissions: ['students.read'] as string[] | undefined },
}))
vi.mock('../session/AuthProvider.tsx', () => ({ useAuth: () => auth }))

beforeEach(() => {
  auth.status = 'authenticated'
  auth.user.effective_permissions = ['students.read']
})

describe('usePermissions', () => {
  it('uses the server grant list even when the user has the admin role', () => {
    const { result } = renderHook(() => usePermissions())
    expect(result.current.can('students', 'read')).toBe(true)
    expect(result.current.can('students', 'delete')).toBe(false)
  })

  it('updates checks and the nested tree after permission revocation', () => {
    auth.user.effective_permissions = ['students.read', 'students.delete']
    const { result, rerender } = renderHook(() => usePermissions())
    expect(result.current.can('students', 'delete')).toBe(true)
    auth.user.effective_permissions = ['students.read']
    rerender()
    expect(result.current.can('students', 'delete')).toBe(false)
    expect(result.current.permissions.students.delete).toBe(false)
  })

  it.each(['restoring', 'unauthenticated', 'authenticating'])('denies grants while %s', (status) => {
    auth.status = status
    auth.user.effective_permissions = ['*']
    const { result } = renderHook(() => usePermissions())
    expect(result.current.can('students', 'read')).toBe(false)
  })

  it('denies missing grants and clears checks on logout', () => {
    auth.user.effective_permissions = undefined
    const { result, rerender } = renderHook(() => usePermissions())
    expect(result.current.can('students', 'read')).toBe(false)
    auth.user.effective_permissions = ['students.read']
    rerender()
    expect(result.current.can('students', 'read')).toBe(true)
    auth.status = 'unauthenticated'
    rerender()
    expect(result.current.can('students', 'read')).toBe(false)
  })
})

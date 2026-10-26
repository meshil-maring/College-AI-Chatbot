import { describe, expect, it } from 'vitest'
import { createPermissions, hasPermission, isPermissionCode, permissionsByRole } from './rbac.ts'

describe('central RBAC permission access', () => {
  it('exposes nested true and false values for the existing role defaults', () => {
    expect(permissionsByRole.admin.students.update).toBe(true)
    expect(permissionsByRole.admin.students.delete).toBe(true)
    expect(permissionsByRole.staff.students.approve).toBe(true)
    expect(permissionsByRole.staff.students.create).toBe(false)
    expect(permissionsByRole.staff.students.delete).toBe(false)
    expect(permissionsByRole.student.profile.own.read).toBe(true)
    expect(permissionsByRole.student.ai.chat).toBe(true)
    expect(permissionsByRole.student.documents.create).toBe(false)
    expect(permissionsByRole.faculty.profile.own.read).toBe(true)
    expect(permissionsByRole.faculty.students.approve).toBe(false)
    expect(permissionsByRole.super_admin.platform.audit.read).toBe(true)
    expect(permissionsByRole.super_admin.students.approve).toBe(false)
  })

  it('checks effective grants without filling in role defaults', () => {
    const access = createPermissions(['students.read', 'profile.own.update'])
    expect(access.can('students', 'read')).toBe(true)
    expect(access.can('students.read')).toBe(true)
    expect(access.can('profile', 'own', 'update')).toBe(true)
    expect(access.permissions.profile.own.update).toBe(true)
    expect(access.permissions.students.delete).toBe(false)
    expect(access.can('students', 'delete')).toBe(false)
    expect(createPermissions([]).can('students', 'delete')).toBe(false)
    expect(createPermissions(undefined).permissions.students.read).toBe(false)
  })

  it('keeps resource wildcard semantics consistent with the existing checker', () => {
    const access = createPermissions(['students.*', 'profile.*'])
    expect(access.can('students', 'delete')).toBe(true)
    expect(access.can('profile', 'own', 'read')).toBe(true)
    expect(access.can('documents', 'delete')).toBe(false)
    expect(createPermissions(['profile.own.*']).can('profile', 'own', 'read')).toBe(false)
    expect(createPermissions(['student.*']).can('students', 'read')).toBe(false)
    expect(createPermissions(['*']).permissions.platform.audit.read).toBe(true)
    expect(hasPermission(undefined, 'students.read')).toBe(false)
  })

  it('requires all or any of the requested permissions and denies empty/unknown requests', () => {
    const access = createPermissions(['students.read', 'students.approve'])
    expect(access.canAll('students.read', 'students.approve')).toBe(true)
    expect(access.canAll('students.read', 'students.reject')).toBe(false)
    expect(access.canAny('students.reject', 'students.approve')).toBe(true)
    expect(access.canAny('students.delete', 'students.create')).toBe(false)
    expect(access.canAll()).toBe(false)
    expect(access.canAny()).toBe(false)
    const wildcard = createPermissions(['*'])
    expect(Reflect.apply(wildcard.can, null, ['students', 'unknown'])).toBe(false)
    expect(Reflect.apply(wildcard.can, null, [])).toBe(false)
    expect(Reflect.apply(wildcard.can, null, ['__proto__', 'update'])).toBe(false)
    expect(isPermissionCode('platform.audit.read')).toBe(true)
    expect(isPermissionCode('students.unknown')).toBe(false)
  })

  it('keeps role defaults and effective grant snapshots immutable', () => {
    const grants = ['students.read']
    const access = createPermissions(grants)
    grants.push('students.delete')
    expect(access.can('students', 'delete')).toBe(false)
    expect(Object.isFrozen(permissionsByRole)).toBe(true)
    expect(Object.isFrozen(permissionsByRole.admin.students)).toBe(true)
    expect(Reflect.set(permissionsByRole.admin.students, 'delete', false)).toBe(false)
    expect(Reflect.set(access.permissions.students, 'delete', true)).toBe(false)
    expect(access.permissions.students.delete).toBe(false)
  })

  it.each([
    'academic.manage',
    'attendance.own.read',
    'attendance.manage',
    'results.manage',
    'faculty.assignments.manage',
  ])('rejects retired academic permission %s even with wildcard grants', (code) => {
    expect(isPermissionCode(code)).toBe(false)
    expect(Reflect.apply(createPermissions(['*']).can, null, [code])).toBe(false)
  })

  it.each([
    'courses.read',
    'courses.manage',
    'departments.read',
    'departments.manage',
    'academic_years.read',
    'academic_years.manage',
    'semesters.read',
    'semesters.manage',
  ])('recognizes approved Academic Setup permission %s', (code) => {
    expect(isPermissionCode(code)).toBe(true)
    expect(Reflect.apply(createPermissions(['*']).can, null, [code])).toBe(true)
  })
})

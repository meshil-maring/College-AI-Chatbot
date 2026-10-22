import { hasPermission } from '../auth/access/permissions.ts'

export function canOpenPackageWorkspace(permissions: readonly string[] | undefined) {
  return [
    'academic.curriculum.read',
    'academic.curriculum.manage',
    'academic.class.read',
    'academic.class.manage',
    'academic.package.assign',
    'academic.package.change',
    'academic.package.requests.review',
    'academic.package.own.read',
    'academic.package.own.select',
    'academic.package.own.request',
  ].some((permission) => hasPermission(permissions ?? [], permission))
}

/** Shared UI permission checks. API role, tenant and academic guards remain authoritative. */
import type { AuthRole } from '../../types/auth.ts'
import { PERMISSION_CODES, ROLE_DEFAULT_PERMISSIONS, type PermissionCode } from './rbacPolicy.generated.ts'

export { PERMISSION_CODES, type PermissionCode } from './rbacPolicy.generated.ts'

type Head<Path extends string> = Path extends `${infer First}.${string}` ? First : Path
type Tail<Path extends string, First extends string> = Path extends `${First}.${infer Rest}` ? Rest : never
type Segments<Path extends string> = Path extends `${infer First}.${infer Rest}` ? [First, ...Segments<Rest>] : [Path]

/** Every catalog leaf exists, including explicitly false permissions. */
export type PermissionTree<Paths extends string = PermissionCode> = {
  readonly [First in Head<Paths>]: [Tail<Paths, First>] extends [never]
    ? boolean : PermissionTree<Tail<Paths, First>>
}

export type PermissionInput = {
  [Code in PermissionCode]: [Code] | Segments<Code>
}[PermissionCode]

const knownCodes: ReadonlySet<string> = new Set(PERMISSION_CODES)

export function isPermissionCode(value: string): value is PermissionCode {
  return knownCodes.has(value)
}

/** Compatibility with existing string-based checks; never infers grants from a role. */
export function hasPermission(granted: readonly string[] | undefined, required: string): boolean {
  if (granted === undefined) return false
  if (granted.includes(required) || granted.includes('*')) return true
  const separator = required.indexOf('.')
  return separator > 0 && granted.includes(`${required.slice(0, separator)}.*`)
}

type MutableTree = { [key: string]: boolean | MutableTree }

function freezeTree(tree: MutableTree): PermissionTree {
  for (const value of Object.values(tree)) {
    if (typeof value === 'object') freezeTree(value)
  }
  return Object.freeze(tree) as PermissionTree
}

function buildTree(granted: readonly string[] | undefined): PermissionTree {
  const root: MutableTree = Object.create(null) as MutableTree
  for (const code of PERMISSION_CODES) {
    const parts = code.split('.')
    let branch = root
    for (const part of parts.slice(0, -1)) {
      const existing = branch[part]
      branch = typeof existing === 'object' ? existing
        : (branch[part] = Object.create(null) as MutableTree)
    }
    branch[parts[parts.length - 1]] = hasPermission(granted, code)
  }
  return freezeTree(root)
}

/**
 * Read-only role bootstrap reference, generated from backend policy.
 * Use createPermissions/usePermissions for a user's live grants and revocations.
 */
export const permissionsByRole: Readonly<Record<AuthRole, PermissionTree>> = Object.freeze(
  Object.fromEntries(Object.entries(ROLE_DEFAULT_PERMISSIONS).map(([role, grants]) => [role, buildTree(grants)])),
) as Readonly<Record<AuthRole, PermissionTree>>

export interface PermissionAccess {
  readonly permissions: PermissionTree
  readonly can: (...permission: PermissionInput) => boolean
  readonly canAll: (...required: readonly PermissionCode[]) => boolean
  readonly canAny: (...required: readonly PermissionCode[]) => boolean
}

/** Build one immutable snapshot from effective permissions supplied by the server. */
export function createPermissions(granted: readonly string[] | undefined): PermissionAccess {
  const snapshot = granted === undefined ? undefined : [...granted]
  const check = (code: string) => isPermissionCode(code) && hasPermission(snapshot, code)
  return Object.freeze({
    permissions: buildTree(snapshot),
    can: (...permission: PermissionInput) => check(permission.join('.')),
    canAll: (...required: readonly PermissionCode[]) => required.length > 0 && required.every(check),
    canAny: (...required: readonly PermissionCode[]) => required.some(check),
  })
}

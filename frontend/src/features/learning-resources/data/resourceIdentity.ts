import type { CurrentUser } from '../../../types/auth.ts'
import type { LearningResource, ResourceRevision } from '../../../types/learningResources.ts'
import { hasPermission } from '../../auth/access/permissions.ts'

export function hasResourceNavigation(role: string | null, grants?: readonly string[]) {
  return (
    ['admin', 'faculty', 'staff'].includes(role ?? '') &&
    (hasPermission(grants, 'documents.read') ||
      hasPermission(grants, 'ai.knowledge.create') ||
      (role === 'admin' && hasPermission(grants, 'ai.knowledge.read')))
  )
}

export function resourceAccess(user: CurrentUser | null) {
  const grants = user?.effective_permissions
  const manager = ['admin', 'faculty', 'staff'].includes(user?.role ?? '')
  const canCreate = manager && hasPermission(grants, 'ai.knowledge.create')
  const canReview = user?.role === 'admin' && hasPermission(grants, 'ai.knowledge.read')
  return {
    canRead: manager && hasPermission(grants, 'documents.read'),
    canAsk: manager && hasPermission(grants, 'ai.chat'),
    canCreate,
    canReview,
    canDecide: canReview && hasPermission(grants, 'ai.knowledge.update'),
    canUpload: canCreate && hasPermission(grants, 'documents.create'),
    canReplace: canCreate && hasPermission(grants, 'documents.update'),
    canEditOthers: user?.role === 'admin' && hasPermission(grants, 'ai.knowledge.update'),
  }
}
export function resourceContext(user: CurrentUser | null, token: string | null, generation: number) {
  if (!user?.institution_id || !token || !['admin', 'faculty', 'staff'].includes(user.role ?? '')) return null
  const access = resourceAccess(user)
  if (!access.canRead && !access.canCreate && !access.canReview) return null
  const identity = JSON.stringify([
    generation,
    user.user_id,
    user.institution_id,
    user.role,
    [...(user.effective_permissions ?? [])].sort(),
  ])
  return { identity, accessToken: token, institutionId: user.institution_id, userId: user.user_id, ...access }
}
export type ResourceContext = NonNullable<ReturnType<typeof resourceContext>>

export function canEditRevision(context: ResourceContext, revision: ResourceRevision) {
  return (
    context.canCreate &&
    revision.lifecycle_status === 'draft' &&
    (revision.created_by_user_id === context.userId || context.canEditOthers)
  )
}
export function canCloneResource(context: ResourceContext, resource: LearningResource | ResourceRevision) {
  if (!context.canCreate || ['faq', 'notice'].includes(resource.source_type)) return false
  return context.canEditOthers || ('created_by_user_id' in resource && resource.created_by_user_id === context.userId)
}

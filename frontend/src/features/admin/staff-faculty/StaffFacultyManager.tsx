import { useRef, useState } from 'react'
import StaffPermissionManager from '../permissions/StaffPermissionManager.tsx'
import type { StaffPermissionFocus } from '../permissions/useStaffPermissions.ts'
import MembershipRequests from './MembershipRequests.tsx'
import MembershipRosterTable from './MembershipRosterTable.tsx'
import { useStaffFacultyManagement } from './useStaffFacultyManagement.ts'

/**
 * Staff and Faculty Management: approve requests as Staff or Faculty into a
 * department chosen by the administrator, keep each member's role and
 * department up to date, and give Staff members extra permissions.
 */
export default function StaffFacultyManager({
  accessToken,
  canManagePermissions = true,
}: {
  accessToken: string
  /** Whether the administrator holds `permissions.read`; the API enforces it either way. */
  canManagePermissions?: boolean
}) {
  const management = useStaffFacultyManagement(accessToken)
  const [permissionFocus, setPermissionFocus] = useState<StaffPermissionFocus | null>(null)
  const permissionsRef = useRef<HTMLDivElement>(null)

  return (
    <div className="space-y-8">
      {management.error ? (
        <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
          {management.error}
        </p>
      ) : null}
      {management.success ? (
        <p role="status" className="rounded-lg border border-success bg-success-bg p-3 text-sm text-success">
          {management.success}
        </p>
      ) : null}

      <MembershipRequests
        requestFilter={management.requestFilter}
        setRequestFilter={management.setRequestFilter}
        requests={management.requests}
        departments={management.departments}
        loading={management.loading}
        actionKey={management.actionKey}
        decide={management.decide}
      />

      <MembershipRosterTable
        members={management.members}
        departments={management.departments}
        loading={management.loading}
        actionKey={management.actionKey}
        lifecycle={management.lifecycle}
        changeDepartment={management.changeDepartment}
        changeRole={management.changeRole}
        headOf={management.headOf}
        makeHod={management.makeHod}
        removeHod={management.removeHod}
        managePermissions={
          canManagePermissions
            ? (member) => {
                setPermissionFocus({ userId: member.user_id, requestedAt: Date.now() })
                permissionsRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
              }
            : undefined
        }
      />

      {canManagePermissions ? (
        <div ref={permissionsRef}>
          {/* Shares this page's cache, so a role change also refreshes it. */}
          <StaffPermissionManager accessToken={accessToken} focus={permissionFocus} />
        </div>
      ) : null}
    </div>
  )
}

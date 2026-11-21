import { UserPlus } from 'lucide-react'
import { useRef, useState } from 'react'
import StaffPermissionManager from '../permissions/StaffPermissionManager.tsx'
import type { StaffPermissionFocus } from '../permissions/useStaffPermissions.ts'
import AddMemberDialog, { type InvitationDraft } from './invitations/AddMemberDialog.tsx'
import PendingInvitations from './invitations/PendingInvitations.tsx'
import { useMemberInvitations } from './invitations/useMemberInvitations.ts'
import MembershipRequests from './requests/MembershipRequests.tsx'
import MembershipRosterTable from './roster/MembershipRosterTable.tsx'
import StaffFacultySummary from './StaffFacultySummary.tsx'
import { Feedback, PRIMARY_BUTTON_CLASS } from './StaffFacultyUI.tsx'
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
  const invitations = useMemberInvitations(accessToken)
  // The open "Add member" dialog and what it starts with (empty, or an expired invitation).
  const [inviteDraft, setInviteDraft] = useState<InvitationDraft | null>(null)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-3">
        <p className="mr-auto text-sm text-muted">
          Invite new Staff or Faculty by email, approve sign-up requests and manage everyone on the roster.
        </p>
        <button
          id="staff-faculty-add-member"
          type="button"
          onClick={() => setInviteDraft({})}
          className={PRIMARY_BUTTON_CLASS}
        >
          <UserPlus aria-hidden="true" className="size-4" />
          Add member
        </button>
      </div>

      <Feedback error={management.error} success={management.success} onDismiss={management.dismiss} />

      <StaffFacultySummary
        pendingCount={management.pendingCount}
        members={management.members}
        headCount={management.headCount}
        loading={management.loading}
      />

      <MembershipRequests
        requestFilter={management.requestFilter}
        setRequestFilter={management.setRequestFilter}
        requests={management.requests}
        departments={management.departments}
        loading={management.loading}
        actionKey={management.actionKey}
        decide={management.decide}
      />

      <PendingInvitations
        model={invitations}
        departments={management.departments}
        onInviteAgain={(invitation) =>
          setInviteDraft({
            full_name: invitation.full_name ?? '',
            email: invitation.email,
            role: invitation.role,
            department_id: invitation.department_id ?? undefined,
          })
        }
      />

      <MembershipRosterTable
        members={management.members}
        departments={management.departments}
        loading={management.loading}
        actionKey={management.actionKey}
        lifecycle={management.lifecycle}
        changeDepartment={management.changeDepartment}
        changeRole={management.changeRole}
        appointmentsOf={management.appointmentsOf}
        coHeadsOf={management.coHeadsOf}
        saveHodDepartments={management.saveHodDepartments}
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
        <div ref={permissionsRef} className="scroll-mt-4">
          {/* Shares this page's cache, so a role change also refreshes it. */}
          <StaffPermissionManager accessToken={accessToken} focus={permissionFocus} />
        </div>
      ) : null}
      {inviteDraft ? (
        <AddMemberDialog
          departments={management.departments}
          initial={inviteDraft}
          sending={invitations.actionKey === 'create'}
          onSubmit={invitations.create}
          onClose={() => setInviteDraft(null)}
        />
      ) : null}
    </div>
  )
}

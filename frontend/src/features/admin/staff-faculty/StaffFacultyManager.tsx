import { UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { StaffFacultyPage } from '../adminNavigation.ts'
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
 * Staff and Faculty Management, one page at a time: Requests, Pending
 * invitations, Roster and Staff permissions. The admin shell owns the page in
 * the URL (`staff-page`); without `page` the component keeps its own state.
 * Reads stay cached across pages, so switching pages shows saved data at once.
 */
export default function StaffFacultyManager({
  accessToken,
  canManagePermissions = true,
  page,
  defaultPage = 'requests',
  onNavigate,
}: {
  accessToken: string
  /** Whether the administrator holds `permissions.read`; the API enforces it either way. */
  canManagePermissions?: boolean
  /** The page chosen in the sidebar. */
  page?: StaffFacultyPage
  /** Starting page when `page` is not controlled. */
  defaultPage?: StaffFacultyPage
  onNavigate?: (page: StaffFacultyPage) => void
}) {
  const management = useStaffFacultyManagement(accessToken)
  const invitations = useMemberInvitations(accessToken)
  const [localPage, setLocalPage] = useState<StaffFacultyPage>(defaultPage)
  const requested = page ?? localPage
  const current = requested === 'permissions' && !canManagePermissions ? 'requests' : requested
  const [permissionFocus, setPermissionFocus] = useState<StaffPermissionFocus | null>(null)
  // The open "Add member" dialog and what it starts with (empty, or an expired invitation).
  const [inviteDraft, setInviteDraft] = useState<InvitationDraft | null>(null)

  function navigate(next: StaffFacultyPage) {
    if (onNavigate) onNavigate(next)
    else setLocalPage(next)
  }

  // A member chosen from the roster applies once; opening the page later starts fresh.
  useEffect(() => {
    if (current !== 'permissions') setPermissionFocus(null)
  }, [current])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-3">
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

      {current !== 'permissions' ? (
        <StaffFacultySummary
          pendingCount={management.pendingCount}
          members={management.members}
          headCount={management.headCount}
          loading={management.loading}
        />
      ) : null}

      {current === 'requests' ? (
        <MembershipRequests
          requestFilter={management.requestFilter}
          setRequestFilter={management.setRequestFilter}
          requests={management.requests}
          departments={management.departments}
          loading={management.loading}
          actionKey={management.actionKey}
          decide={management.decide}
        />
      ) : null}

      {current === 'invitations' ? (
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
      ) : null}

      {current === 'roster' ? (
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
                  navigate('permissions')
                }
              : undefined
          }
        />
      ) : null}

      {current === 'permissions' ? (
        // Shares this page's cache, so a role change also refreshes it.
        <StaffPermissionManager accessToken={accessToken} focus={permissionFocus} />
      ) : null}

      {inviteDraft ? (
        <AddMemberDialog
          departments={management.departments}
          initial={inviteDraft}
          sending={invitations.actionKey === 'create'}
          onSubmit={async (draft) => {
            const failure = await invitations.create(draft)
            // Show the new invitation where it now lives.
            if (failure === null) navigate('invitations')
            return failure
          }}
          onClose={() => setInviteDraft(null)}
        />
      ) : null}
    </div>
  )
}

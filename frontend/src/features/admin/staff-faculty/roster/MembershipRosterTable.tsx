import { Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MemberInvitation, MembershipRosterEntry } from '../../../../types/admin.ts'
import type { InstitutionAdmin } from '../../../../types/admin/administrators.ts'
import type { StaffFacultyPage } from '../../adminNavigation.ts'
import MemberHistoryDialog from '../history/MemberHistoryDialog.tsx'
import EditProfileDialog from '../profile/EditProfileDialog.tsx'
import { BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import type { HeadSelection } from '../useDepartmentHeadActions.ts'
import HodDialog from './HodDialog.tsx'
import { buildDirectory } from './directoryItems.ts'
import DirectoryReadOnlyRow from './DirectoryReadOnlyRow.tsx'
import MembershipRosterRow, { type RosterActions } from './MembershipRosterRow.tsx'
import RosterToolbar from './RosterToolbar.tsx'
import { useRosterFilters } from './useRosterFilters.ts'

interface Props extends RosterActions {
  accessToken: string
  members: MembershipRosterEntry[]
  /** Administrators and waiting invitations, listed read-only beside members. */
  admins: InstitutionAdmin[]
  invitations: MemberInvitation[]
  onOpenPage: (page: StaffFacultyPage) => void
  /** Show a result message on the page. */
  notify: (message: string) => void
  departments: Department[]
  loading: boolean
  coHeadsOf: (departmentId: string, exceptUserId: string) => string[]
  saveHodDepartments: (member: MembershipRosterEntry, selections: HeadSelection[]) => Promise<void>
  /** Institution policy: may one faculty member head several departments? */
  allowMultiHod: boolean
}

/**
 * The institution's user directory: Staff and Faculty with their role,
 * departments, employee details and status, plus administrators and pending
 * invitations (managed on their own pages). Members' profiles, status and
 * history are managed from each row's actions.
 */
export default function MembershipRosterTable({
  accessToken,
  members,
  admins,
  invitations,
  onOpenPage,
  notify,
  departments,
  loading,
  coHeadsOf,
  saveHodDepartments,
  allowMultiHod,
  ...actions
}: Props) {
  const items = useMemo(
    () => buildDirectory(members, admins, invitations, departments),
    [members, admins, invitations, departments],
  )
  const filters = useRosterFilters(items)
  const [open, setOpen] = useState<{ dialog: 'hod' | 'profile' | 'history'; userId: string } | null>(null)
  // Read the member from the latest roster so a refresh never shows stale data.
  const openMember = members.find((member) => member.user_id === open?.userId) ?? null
  const hodMember = open?.dialog === 'hod' ? openMember : null
  const show = (dialog: 'hod' | 'profile' | 'history') => (member: MembershipRosterEntry) =>
    setOpen({ dialog, userId: member.user_id })
  const rowActions = { ...actions, openHod: show('hod'), openProfile: show('profile'), openHistory: show('history') }
  const close = () => setOpen(null)

  return (
    <section
      aria-labelledby="membership-roster-heading"
      className="space-y-4 rounded-xl border border-line bg-surface p-4"
    >
      <div>
        <h2 id="membership-roster-heading" className="sr-only">
          Roster
        </h2>
        <p className="mt-1 max-w-[70ch] text-sm text-muted">
          Everyone in your institution: Staff, Faculty, administrators and pending invitations. Change a member&apos;s
          role or department here; use each row&apos;s actions to edit their profile, appoint HODs, suspend or
          deactivate them, or see their history.
        </p>
      </div>
      {loading ? (
        <p role="status" className="text-sm text-muted">
          Loading roster…
        </p>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Users aria-hidden="true" className="size-8 text-muted" />
          <p className="text-sm text-muted">No staff or faculty are on the roster yet.</p>
          <p className="text-xs text-muted">Approved requests appear here.</p>
        </div>
      ) : (
        <>
          <RosterToolbar filters={filters} departments={departments} total={items.length} />
          {filters.visible.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <p className="text-sm text-muted">No members match these filters.</p>
              <button type="button" onClick={filters.clear} className={BUTTON_CLASS}>
                Clear filters
              </button>
            </div>
          ) : (
            <div
              role="region"
              aria-label="Staff and faculty roster"
              tabIndex={0}
              className="ui-card-table-region overflow-x-auto rounded-lg border border-line"
            >
              <table className="ui-card-table w-full min-w-[960px] text-left text-sm">
                <thead className="bg-raised text-xs text-muted">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Member
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Employee
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Role
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Department
                    </th>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Status
                    </th>
                    <th scope="col" className="px-4 py-3 text-right font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filters.visible.map((item) =>
                    item.member ? (
                      <MembershipRosterRow
                        key={item.key}
                        member={item.member}
                        departments={departments}
                        actions={rowActions}
                      />
                    ) : (
                      <DirectoryReadOnlyRow key={item.key} item={item} onOpenPage={onOpenPage} />
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {hodMember ? (
        <HodDialog
          member={hodMember}
          departments={departments}
          appointments={actions.appointmentsOf(hodMember)}
          coHeadsOf={coHeadsOf}
          canAppoint={hodMember.role === 'faculty' && hodMember.status === 'active'}
          allowMulti={allowMultiHod}
          saving={actions.actionKey === `hod:${hodMember.user_id}`}
          onSave={(selections) => {
            void saveHodDepartments(hodMember, selections).then(close)
          }}
          onClose={close}
        />
      ) : null}
      {open?.dialog === 'profile' && openMember ? (
        <EditProfileDialog
          accessToken={accessToken}
          member={openMember}
          departments={departments}
          onSaved={(message) => {
            notify(message)
            close()
          }}
          onClose={close}
        />
      ) : null}
      {open?.dialog === 'history' && openMember ? (
        <MemberHistoryDialog accessToken={accessToken} member={openMember} onClose={close} />
      ) : null}
    </section>
  )
}

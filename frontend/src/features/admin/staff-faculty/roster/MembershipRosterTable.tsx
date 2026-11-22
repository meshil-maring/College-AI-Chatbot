import { Users } from 'lucide-react'
import { useState } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import { BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import type { HeadSelection } from '../useDepartmentHeadActions.ts'
import HodDialog from './HodDialog.tsx'
import MembershipRosterRow, { type RosterActions } from './MembershipRosterRow.tsx'
import RosterToolbar from './RosterToolbar.tsx'
import { useRosterFilters } from './useRosterFilters.ts'

interface Props extends RosterActions {
  members: MembershipRosterEntry[]
  departments: Department[]
  loading: boolean
  coHeadsOf: (departmentId: string, exceptUserId: string) => string[]
  saveHodDepartments: (member: MembershipRosterEntry, selections: HeadSelection[]) => Promise<void>
  /** Institution policy: may one faculty member head several departments? */
  allowMultiHod: boolean
}

/**
 * Approved Staff and Faculty with the role and department the administrator
 * assigned. Faculty can also be made Head of Department of their department.
 */
export default function MembershipRosterTable({
  members,
  departments,
  loading,
  coHeadsOf,
  saveHodDepartments,
  allowMultiHod,
  ...actions
}: Props) {
  const filters = useRosterFilters(members)
  const [hodUserId, setHodUserId] = useState<string | null>(null)
  // Read the member from the latest roster so a refresh never shows stale data.
  const hodMember = members.find((member) => member.user_id === hodUserId) ?? null
  const rowActions = { ...actions, openHod: (member: MembershipRosterEntry) => setHodUserId(member.user_id) }

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
          Change a member&apos;s role or department here. Make HOD appoints a Faculty member as Head of their
          department. Use Permissions to give a Staff member extra duties.
        </p>
      </div>
      {loading ? (
        <p role="status" className="text-sm text-muted">
          Loading roster…
        </p>
      ) : members.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Users aria-hidden="true" className="size-8 text-muted" />
          <p className="text-sm text-muted">No staff or faculty are on the roster yet.</p>
          <p className="text-xs text-muted">Approved requests appear here.</p>
        </div>
      ) : (
        <>
          <RosterToolbar filters={filters} departments={departments} total={members.length} />
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
              <table className="ui-card-table w-full min-w-[800px] text-left text-sm">
                <thead className="bg-raised text-xs text-muted">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-medium">
                      Member
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
                  {filters.visible.map((member) => (
                    <MembershipRosterRow
                      key={member.user_id}
                      member={member}
                      departments={departments}
                      actions={rowActions}
                    />
                  ))}
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
            void saveHodDepartments(hodMember, selections).then(() => setHodUserId(null))
          }}
          onClose={() => setHodUserId(null)}
        />
      ) : null}
    </section>
  )
}

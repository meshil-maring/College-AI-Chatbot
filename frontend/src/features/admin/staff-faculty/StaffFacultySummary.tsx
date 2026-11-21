import type { MembershipRosterEntry } from '../../../types/admin.ts'

interface Props {
  /** Pending requests, or null while they have not loaded. */
  pendingCount: number | null
  members: MembershipRosterEntry[]
  headCount: number
  loading: boolean
}

/** At-a-glance counts for the page: what needs a decision and who is on the roster. */
export default function StaffFacultySummary({ pendingCount, members, headCount, loading }: Props) {
  const active = members.filter((member) => member.status === 'active')
  const unassigned = active.filter((member) => member.department_id === null).length
  const tiles = [
    {
      label: 'Awaiting approval',
      value: pendingCount,
      hint: pendingCount ? 'Choose a role and department to approve' : 'No requests waiting',
      highlight: Boolean(pendingCount),
    },
    {
      label: 'Active faculty (teachers)',
      value: active.filter((member) => member.role === 'faculty').length,
      hint:
        headCount === 0
          ? 'No Heads of Department yet'
          : `${headCount} ${headCount === 1 ? 'is Head' : 'are Heads'} of Department`,
    },
    {
      label: 'Active staff',
      value: active.filter((member) => member.role === 'staff').length,
      hint: 'Give extra duties with Permissions',
    },
    {
      label: 'Without a department',
      value: unassigned,
      hint: unassigned ? 'Assign one from the roster' : 'Everyone is assigned',
      highlight: unassigned > 0,
    },
  ]
  return (
    <section aria-label="Staff and faculty summary" className="@container">
      <dl className="grid grid-cols-1 gap-3 @[521px]:grid-cols-2 @[1051px]:grid-cols-4">
        {tiles.map((tile) => (
          <div
            key={tile.label}
            className={`rounded-xl border bg-surface p-4 ${tile.highlight ? 'border-warning' : 'border-line'}`}
          >
            <dt className="text-sm font-medium text-muted">{tile.label}</dt>
            <dd className="mt-1 text-[1.75rem] leading-tight font-bold tabular-nums text-content">
              {loading || tile.value === null ? '—' : tile.value}
            </dd>
            <dd className="mt-1 text-xs text-muted">{tile.hint}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

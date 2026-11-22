import type { StaffFacultyPage } from '../../adminNavigation.ts'
import { Badge, BUTTON_CLASS, Initials, StatusBadge } from '../StaffFacultyUI.tsx'
import type { DirectoryItem } from './directoryItems.ts'

const TYPE_LABELS = { admin: 'Administrator', faculty: 'Faculty (Teacher)', staff: 'Staff' } as const

/**
 * An administrator or a pending invitation in the directory. They are managed
 * on their own pages, so the row links there instead of offering actions.
 */
export default function DirectoryReadOnlyRow({
  item,
  onOpenPage,
}: {
  item: DirectoryItem
  onOpenPage: (page: StaffFacultyPage) => void
}) {
  const page: StaffFacultyPage = item.admin ? 'administrators' : 'invitations'
  return (
    <tr className="border-t border-line align-top hover:bg-hover/40">
      <td className="px-4 py-3">
        <div className="flex items-start gap-3">
          <Initials name={item.name} />
          <div className="min-w-0">
            <p className="font-medium text-content">{item.name}</p>
            <p className="break-all text-xs text-muted">{item.email}</p>
          </div>
        </div>
      </td>
      <td data-label="Employee" className="px-4 py-3 text-sm">
        <p className="text-content">{item.employeeId ?? '—'}</p>
        {item.designation ? <p className="text-xs text-muted">{item.designation}</p> : null}
      </td>
      <td data-label="Role" className="px-4 py-3 text-sm">
        <span className="flex flex-wrap items-center gap-1">
          {TYPE_LABELS[item.userType]}
          {item.admin?.is_owner ? <Badge tone="accent">Owner</Badge> : null}
        </span>
      </td>
      <td data-label="Department" className="px-4 py-3 text-sm text-muted">
        {item.departmentName ?? (item.admin ? 'Whole institution' : '—')}
      </td>
      <td data-label="Status" className="whitespace-nowrap px-4 py-3">
        <StatusBadge status={item.status} />
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => onOpenPage(page)}
            aria-label={item.admin ? `Manage ${item.name} on Administrators` : `Open the invitation for ${item.name}`}
            className={BUTTON_CLASS}
          >
            {item.admin ? 'Administrators' : 'Invitations'}
          </button>
        </div>
      </td>
    </tr>
  )
}

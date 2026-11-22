import { X } from 'lucide-react'
import { useId } from 'react'
import { useQuery } from '@tanstack/react-query'
import { queryClient } from '../../../../lib/queryClient.ts'
import { getMemberHistory } from '../../../../services/admin/adminApi.ts'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import { BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import { staffFacultyKeys } from '../staffFacultyKeys.ts'

function when(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** A short, readable summary of what changed, from the recorded details. */
function summary(details: Record<string, unknown>) {
  const parts: string[] = []
  if (typeof details.from === 'string' && typeof details.to === 'string') parts.push(`${details.from} → ${details.to}`)
  if (typeof details.status === 'string') parts.push(`now ${details.status}`)
  if (typeof details.responsibility === 'string') parts.push(details.responsibility.replaceAll('_', ' '))
  if (typeof details.planned_end_on === 'string') parts.push(`planned end ${details.planned_end_on}`)
  return parts.join(' · ')
}

/** Who changed what for one member, newest first. Records are kept after people leave. */
export default function MemberHistoryDialog({
  accessToken,
  member,
  onClose,
}: {
  accessToken: string
  member: MembershipRosterEntry
  onClose: () => void
}) {
  const ref = useWorkspaceDialog('#membership-roster-heading')
  const id = useId()
  const query = useQuery(
    {
      queryKey: staffFacultyKeys.history(accessToken, member.user_id),
      queryFn: () => getMemberHistory(accessToken, member.user_id),
      staleTime: 0,
    },
    queryClient,
  )
  const entries = query.data?.entries ?? []

  return (
    <dialog
      ref={ref}
      aria-labelledby={`${id}-title`}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      className="m-auto flex max-h-[min(640px,100dvh)] w-[min(560px,100vw)] flex-col rounded-xl border border-line bg-surface p-0 text-content shadow-overlay backdrop:bg-[var(--ui-overlay)]"
    >
      <header className="flex items-start gap-3 border-b border-line p-5">
        <div className="mr-auto min-w-0">
          <h2 id={`${id}-title`} className="text-section font-semibold">
            Account history
          </h2>
          <p className="mt-1 break-all text-sm text-muted">{member.name || member.email}</p>
        </div>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg hover:bg-hover"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {query.isPending ? (
          <p role="status" className="text-sm text-muted">
            Loading history…
          </p>
        ) : query.error ? (
          <p role="alert" className="text-sm text-danger">
            {query.error instanceof Error ? query.error.message : 'Could not load the history.'}
          </p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted">No recorded changes yet.</p>
        ) : (
          <ol aria-label="Changes" className="space-y-3">
            {entries.map((entry) => (
              <li key={entry.audit_id} className="border-l-2 border-line pl-3 text-sm">
                <p className="font-medium text-content">{entry.label}</p>
                {summary(entry.details) ? <p className="text-muted">{summary(entry.details)}</p> : null}
                <p className="text-xs text-muted">
                  {when(entry.performed_at)} · by {entry.actor_name}
                </p>
              </li>
            ))}
          </ol>
        )}
      </div>
      <footer className="flex justify-end border-t border-line p-5">
        <button type="button" onClick={onClose} className={BUTTON_CLASS}>
          Close
        </button>
      </footer>
    </dialog>
  )
}

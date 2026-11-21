import { useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { hasPermission } from '../../auth/access/permissions.ts'
import { useStudentNotifications } from './useStudentNotifications.ts'

type Filter = 'all' | 'unread'

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** The student's own notifications, such as transfer decisions. */
export default function NotificationsPage({ onOpenTransfers }: { onOpenTransfers?: () => void }) {
  const { accessToken, user, role, sessionGeneration } = useAuth()
  const permissions = user?.effective_permissions
  if (
    !accessToken ||
    !user?.institution_id ||
    role !== 'student' ||
    !hasPermission(permissions, 'notifications.own.read')
  )
    return <p role="status">Notifications are unavailable for this account.</p>
  const identity = JSON.stringify([sessionGeneration ?? 0, user.user_id, user.institution_id, role])
  return (
    <NotificationSession
      key={identity}
      identity={identity}
      institutionId={user.institution_id}
      token={accessToken}
      canMarkRead={hasPermission(permissions, 'notifications.own.update')}
      onOpenTransfers={onOpenTransfers}
    />
  )
}

function NotificationSession({
  identity,
  institutionId,
  token,
  canMarkRead,
  onOpenTransfers,
}: {
  identity: string
  institutionId: string
  token: string
  canMarkRead: boolean
  onOpenTransfers?: () => void
}) {
  const [filter, setFilter] = useState<Filter>('all')
  const { query, markRead } = useStudentNotifications(identity, institutionId, token)
  const items = query.data?.items ?? []
  const unread = items.filter((item) => !item.is_read)
  const shown = filter === 'unread' ? unread : items
  const error = query.error ?? markRead.error
  return (
    <section className="space-y-4" aria-label="Notifications">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2" role="group" aria-label="Filter notifications">
          {(['all', 'unread'] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
              className={`min-h-10 rounded-full border px-3 text-sm ${
                filter === value ? 'border-accent bg-accent text-ink' : 'border-control hover:bg-hover'
              }`}
            >
              {value === 'all' ? `All (${items.length})` : `Unread (${unread.length})`}
            </button>
          ))}
        </div>
        {canMarkRead && unread.length > 0 && (
          <button
            type="button"
            disabled={markRead.isPending}
            onClick={() => markRead.mutate(unread.map((item) => item.notification_id))}
            className="min-h-10 rounded-lg border border-control px-3 text-sm hover:bg-hover disabled:opacity-50"
          >
            {markRead.isPending ? 'Saving…' : 'Mark all as read'}
          </button>
        )}
      </div>
      {query.isPending && <p role="status">Loading notifications…</p>}
      {error instanceof Error && (
        <div role="alert" className="ui-panel flex flex-wrap items-center justify-between gap-3 p-4">
          <p>{error.message}</p>
          <button
            type="button"
            onClick={() => void query.refetch()}
            className="min-h-10 rounded-lg border border-control px-4 hover:bg-hover"
          >
            Retry
          </button>
        </div>
      )}
      {query.data && !shown.length && (
        <p role="status" className="ui-panel p-6 text-center text-muted">
          {filter === 'unread' ? 'You have no unread notifications.' : 'You have no notifications yet.'}
        </p>
      )}
      <ul className="space-y-3" aria-label="Notification list">
        {shown.map((item) => (
          <li
            key={item.notification_id}
            className={`ui-panel space-y-2 p-4 ${item.is_read ? '' : 'border-l-4 border-l-accent'}`}
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold text-content">
                {!item.is_read && <span className="sr-only">Unread: </span>}
                {item.title}
              </h3>
              <span className="text-xs text-muted">{formatDate(item.created_at)}</span>
            </div>
            <p className="text-sm text-content">{item.message}</p>
            <div className="flex flex-wrap gap-2">
              {item.source_type === 'student_transfer' && onOpenTransfers && (
                <button
                  type="button"
                  onClick={onOpenTransfers}
                  className="min-h-10 rounded-lg border border-control px-3 text-sm hover:bg-hover"
                >
                  Open Transfer Requests
                </button>
              )}
              {canMarkRead && !item.is_read && (
                <button
                  type="button"
                  disabled={markRead.isPending}
                  onClick={() => markRead.mutate([item.notification_id])}
                  className="min-h-10 rounded-lg px-3 text-sm text-content hover:bg-hover disabled:opacity-50"
                >
                  Mark as read
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

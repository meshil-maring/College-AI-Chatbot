/**
 * Phase Admin-4 — Notice manager.
 *
 * CRUD for notices with publish/unpublish and pin/unpin.
 */

import { useCallback, useEffect, useState } from 'react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { deleteNotice, listNotices, updateNotice } from '../../../services/admin/adminApi.ts'
import type { Notice } from '../../../types/admin.ts'
import NoticeForm from './NoticeForm.tsx'

export default function NoticeManager() {
  const { accessToken } = useAuth()
  const [notices, setNotices] = useState<Notice[]>([])
  const noticesQuery = useApiQuery<Notice[]>(
    ['admin', 'notices', accessToken],
    () => listNotices(accessToken as string),
    accessToken !== null,
  )
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Notice | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  useEffect(() => {
    if (noticesQuery.isFetching) setIsLoading(true)
    if (noticesQuery.data) {
      setNotices(noticesQuery.data)
      setIsLoading(false)
    }
    if (noticesQuery.isError) {
      setError(noticesQuery.error instanceof Error ? noticesQuery.error.message : 'Failed to load notices.')
      setIsLoading(false)
    }
  }, [noticesQuery.data, noticesQuery.error, noticesQuery.isError, noticesQuery.isFetching])

  const handleDelete = useCallback(
    async (id: string) => {
      if (accessToken === null) return
      if (!window.confirm('Delete this notice?')) return
      try {
        await deleteNotice(accessToken, id)
        setNotices((prev) => prev.filter((n) => n.notice_id !== id))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete notice.')
      }
    },
    [accessToken],
  )

  const handleToggleActive = useCallback(
    async (notice: Notice) => {
      if (accessToken === null) return
      try {
        const updated = await updateNotice(accessToken, notice.notice_id, { is_active: !notice.is_active })
        setNotices((prev) => prev.map((n) => (n.notice_id === updated.notice_id ? updated : n)))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update notice.')
      }
    },
    [accessToken],
  )

  if (isLoading) return <div className="text-muted py-8">Loading notices…</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-bold text-content text-section">Notices</h2>
        <button
          type="button"
          onClick={() => {
            setEditing(null)
            setIsFormOpen(true)
          }}
          className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Add Notice
        </button>
      </div>
      {error !== null && (
        <div role="alert" className="rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}
      {isFormOpen && (
        <NoticeForm
          initial={editing}
          onClose={() => setIsFormOpen(false)}
          onSaved={(notice) => {
            setNotices((prev) => {
              const exists = prev.some((n) => n.notice_id === notice.notice_id)
              return exists ? prev.map((n) => (n.notice_id === notice.notice_id ? notice : n)) : [...prev, notice]
            })
            setIsFormOpen(false)
          }}
        />
      )}
      {notices.length === 0 ? (
        <p className="text-sm text-muted">No notices yet.</p>
      ) : (
        <ul className="space-y-2">
          {notices.map((notice) => (
            <li key={notice.notice_id} className="rounded-lg border border-line bg-surface px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1 basis-full sm:basis-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-content break-words">{notice.title}</span>
                    {!notice.is_active && (
                      <span className="rounded bg-raised px-2 py-0.5 text-xs text-muted">draft</span>
                    )}
                    {notice.is_pinned && (
                      <span className="rounded bg-warning-bg px-2 py-0.5 text-xs text-warning">pinned</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted line-clamp-2">{notice.content}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleToggleActive(notice)}
                    className="rounded border border-control bg-surface px-2 py-1 text-xs text-muted hover:bg-hover"
                  >
                    {notice.is_active ? 'Unpublish' : 'Publish'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(notice)
                      setIsFormOpen(true)
                    }}
                    className="rounded border border-control bg-surface px-2 py-1 text-xs text-muted hover:bg-hover"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(notice.notice_id)}
                    className="rounded border border-danger bg-danger-bg px-2 py-1 text-xs text-danger hover:bg-danger-bg"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

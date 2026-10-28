import { useCallback, useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { createNotice, updateNotice } from '../../../services/admin/adminApi.ts'
import type { Notice, NoticeCreate } from '../../../types/admin.ts'

export default function NoticeForm({
  initial,
  onClose,
  onSaved,
}: {
  initial: Notice | null
  onClose: () => void
  onSaved: (notice: Notice) => void
}) {
  const { accessToken } = useAuth()
  const [title, setTitle] = useState(initial?.title ?? '')
  const [content, setContent] = useState(initial?.content ?? '')
  const [category, setCategory] = useState(initial?.category ?? 'general')
  const [priority, setPriority] = useState(initial?.priority ?? 'normal')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(async () => {
    if (accessToken === null) return
    if (title.trim().length === 0 || content.trim().length === 0) {
      setError('Title and content are required.')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      const payload: NoticeCreate = {
        title: title.trim(),
        content: content.trim(),
        category: category.trim() || 'general',
        priority: priority.trim() || 'normal',
      }
      const saved = initial
        ? await updateNotice(accessToken, initial.notice_id, payload)
        : await createNotice(accessToken, payload)
      onSaved(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save notice.')
      setIsSaving(false)
    }
  }, [accessToken, title, content, category, priority, initial, onSaved])

  return (
    <div className="rounded-lg border border-line bg-surface p-4 space-y-3">
      <h3 className="font-semibold text-content text-card">{initial ? 'Edit Notice' : 'New Notice'}</h3>
      {error !== null && (
        <div role="alert" className="rounded border border-danger bg-danger-bg px-3 py-1.5 text-xs text-danger">
          {error}
        </div>
      )}
      <label className="block">
        <span className="text-xs text-muted">Title</span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </label>
      <label className="block">
        <span className="text-xs text-muted">Content</span>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs text-muted">Category</span>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </label>
        <label className="block">
          <span className="text-xs text-muted">Priority</span>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>
      </div>
      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSaving}
          className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-ink hover:bg-accent-hover disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-accent"
        >
          {isSaving ? 'Saving…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-control bg-surface px-3 py-1.5 text-sm text-muted hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

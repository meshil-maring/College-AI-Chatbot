/**
 * Phase Admin-4 — Notice manager.
 *
 * CRUD for notices with publish/unpublish and pin/unpin.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import {
  createNotice,
  deleteNotice,
  listNotices,
  updateNotice,
} from '../../services/adminApi.ts'
import type { Notice, NoticeCreate } from '../../types/admin.ts'

export default function NoticeManager() {
  const { accessToken } = useAuth()
  const [notices, setNotices] = useState<Notice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Notice | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const load = useCallback(async () => {
    if (accessToken === null) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listNotices(accessToken)
      setNotices(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notices.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken])

  useEffect(() => {
    void load()
  }, [load])

  const handleDelete = useCallback(async (id: string) => {
    if (accessToken === null) return
    if (!window.confirm('Delete this notice?')) return
    try {
      await deleteNotice(accessToken, id)
      setNotices((prev) => prev.filter((n) => n.notice_id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete notice.')
    }
  }, [accessToken])

  const handleToggleActive = useCallback(async (notice: Notice) => {
    if (accessToken === null) return
    try {
      const updated = await updateNotice(accessToken, notice.notice_id, { is_active: !notice.is_active })
      setNotices((prev) => prev.map((n) => (n.notice_id === updated.notice_id ? updated : n)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update notice.')
    }
  }, [accessToken])

  if (isLoading) return <div className="text-slate-400 py-8">Loading notices…</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Notices</h2>
        <button type="button" onClick={() => { setEditing(null); setIsFormOpen(true) }} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400">Add Notice</button>
      </div>
      {error !== null && <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
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
        <p className="text-sm text-slate-400">No notices yet.</p>
      ) : (
        <ul className="space-y-2">
          {notices.map((notice) => (
            <li key={notice.notice_id} className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white truncate">{notice.title}</span>
                    {!notice.is_active && <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">draft</span>}
                    {notice.is_pinned && <span className="rounded bg-amber-900/40 px-1.5 py-0.5 text-[10px] text-amber-300">pinned</span>}
                  </div>
                  <p className="mt-1 text-xs text-slate-400 line-clamp-2">{notice.content}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button type="button" onClick={() => handleToggleActive(notice)} className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700">{notice.is_active ? 'Unpublish' : 'Publish'}</button>
                  <button type="button" onClick={() => { setEditing(notice); setIsFormOpen(true) }} className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700">Edit</button>
                  <button type="button" onClick={() => handleDelete(notice.notice_id)} className="rounded border border-red-900/50 bg-red-500/10 px-2 py-1 text-xs text-red-300 hover:bg-red-500/20">Delete</button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function NoticeForm({ initial, onClose, onSaved }: { initial: Notice | null; onClose: () => void; onSaved: (notice: Notice) => void }) {
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
      const payload: NoticeCreate = { title: title.trim(), content: content.trim(), category: category.trim() || 'general', priority: priority.trim() || 'normal' }
      const saved = initial ? await updateNotice(accessToken, initial.notice_id, payload) : await createNotice(accessToken, payload)
      onSaved(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save notice.')
      setIsSaving(false)
    }
  }, [accessToken, title, content, category, priority, initial, onSaved])

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-3">
      <h3 className="text-sm font-semibold text-white">{initial ? 'Edit Notice' : 'New Notice'}</h3>
      {error !== null && <div role="alert" className="rounded border border-red-900/50 bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</div>}
      <label className="block">
        <span className="text-xs text-slate-400">Title</span>
        <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
      </label>
      <label className="block">
        <span className="text-xs text-slate-400">Content</span>
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs text-slate-400">Category</span>
          <input type="text" value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
        </label>
        <label className="block">
          <span className="text-xs text-slate-400">Priority</span>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>
      </div>
      <div className="flex items-center gap-2 pt-1">
        <button type="button" onClick={handleSubmit} disabled={isSaving} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-emerald-400">{isSaving ? 'Saving…' : 'Save'}</button>
        <button type="button" onClick={onClose} className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400">Cancel</button>
      </div>
    </div>
  )
}

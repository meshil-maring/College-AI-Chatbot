/**
 * Phase Admin-4 — FAQ manager.
 *
 * CRUD for FAQs with publish/unpublish. Uses the admin API client.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import {
  createFaq,
  deleteFaq,
  listFaqs,
  updateFaq,
} from '../../services/adminApi.ts'
import type { Faq, FaqCreate } from '../../types/admin.ts'

export default function FaqManager() {
  const { accessToken } = useAuth()
  const [faqs, setFaqs] = useState<Faq[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Faq | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const load = useCallback(async () => {
    if (accessToken === null) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await listFaqs(accessToken)
      setFaqs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load FAQs.')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken])

  useEffect(() => {
    void load()
  }, [load])

  const handleDelete = useCallback(async (id: string) => {
    if (accessToken === null) return
    if (!window.confirm('Delete this FAQ?')) return
    try {
      await deleteFaq(accessToken, id)
      setFaqs((prev) => prev.filter((f) => f.faq_id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete FAQ.')
    }
  }, [accessToken])

  const handleToggleActive = useCallback(async (faq: Faq) => {
    if (accessToken === null) return
    try {
      const updated = await updateFaq(accessToken, faq.faq_id, { is_active: !faq.is_active })
      setFaqs((prev) => prev.map((f) => (f.faq_id === updated.faq_id ? updated : f)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update FAQ.')
    }
  }, [accessToken])

  if (isLoading) {
    return <div className="text-slate-400 py-8">Loading FAQs…</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">FAQs</h2>
        <button
          type="button"
          onClick={() => { setEditing(null); setIsFormOpen(true) }}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Add FAQ
        </button>
      </div>

      {error !== null && (
        <div role="alert" className="rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {isFormOpen && (
        <FaqForm
          initial={editing}
          onClose={() => setIsFormOpen(false)}
          onSaved={(faq) => {
            setFaqs((prev) => {
              const exists = prev.some((f) => f.faq_id === faq.faq_id)
              return exists ? prev.map((f) => (f.faq_id === faq.faq_id ? faq : f)) : [...prev, faq]
            })
            setIsFormOpen(false)
          }}
        />
      )}

      {faqs.length === 0 ? (
        <p className="text-sm text-slate-400">No FAQs yet.</p>
      ) : (
        <ul className="space-y-2">
          {faqs.map((faq) => (
            <li key={faq.faq_id} className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white truncate">{faq.question}</span>
                    {!faq.is_active && (
                      <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">draft</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-400 line-clamp-2">{faq.answer}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleToggleActive(faq)}
                    className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
                  >
                    {faq.is_active ? 'Unpublish' : 'Publish'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setEditing(faq); setIsFormOpen(true) }}
                    className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(faq.faq_id)}
                    className="rounded border border-red-900/50 bg-red-500/10 px-2 py-1 text-xs text-red-300 hover:bg-red-500/20"
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

function FaqForm({
  initial,
  onClose,
  onSaved,
}: {
  initial: Faq | null
  onClose: () => void
  onSaved: (faq: Faq) => void
}) {
  const { accessToken } = useAuth()
  const [question, setQuestion] = useState(initial?.question ?? '')
  const [answer, setAnswer] = useState(initial?.answer ?? '')
  const [category, setCategory] = useState(initial?.category ?? 'general')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(async () => {
    if (accessToken === null) return
    if (question.trim().length === 0 || answer.trim().length === 0) {
      setError('Question and answer are required.')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      const payload: FaqCreate = { question: question.trim(), answer: answer.trim(), category: category.trim() || 'general' }
      const saved = initial
        ? await updateFaq(accessToken, initial.faq_id, payload)
        : await createFaq(accessToken, payload)
      onSaved(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save FAQ.')
      setIsSaving(false)
    }
  }, [accessToken, question, answer, category, initial, onSaved])

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-3">
      <h3 className="text-sm font-semibold text-white">{initial ? 'Edit FAQ' : 'New FAQ'}</h3>
      {error !== null && (
        <div role="alert" className="rounded border border-red-900/50 bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</div>
      )}
      <label className="block">
        <span className="text-xs text-slate-400">Question</span>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        />
      </label>
      <label className="block">
        <span className="text-xs text-slate-400">Answer</span>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        />
      </label>
      <label className="block">
        <span className="text-xs text-slate-400">Category</span>
        <input
          type="text"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        />
      </label>
      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSaving}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          {isSaving ? 'Saving…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

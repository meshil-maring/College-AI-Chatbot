import { useCallback, useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { createFaq, updateFaq } from '../../../services/admin/adminApi.ts'
import type { Faq, FaqCreate } from '../../../types/admin.ts'

/** Create or edit one FAQ. Saves through the admin API and reports the saved FAQ. */
export default function FaqForm({
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
      const payload: FaqCreate = {
        question: question.trim(),
        answer: answer.trim(),
        category: category.trim() || 'general',
      }
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
    <div className="rounded-lg border border-line bg-surface p-4 space-y-3">
      <h3 className="font-semibold text-content text-card">{initial ? 'Edit FAQ' : 'New FAQ'}</h3>
      {error !== null && (
        <div role="alert" className="rounded border border-danger bg-danger-bg px-3 py-2 text-xs text-danger">
          {error}
        </div>
      )}
      <label className="block">
        <span className="text-xs text-muted">Question</span>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </label>
      <label className="block">
        <span className="text-xs text-muted">Answer</span>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </label>
      <label className="block">
        <span className="text-xs text-muted">Category</span>
        <input
          type="text"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="mt-1 w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </label>
      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSaving}
          className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink hover:bg-accent-hover disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-accent"
        >
          {isSaving ? 'Saving…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-control bg-surface px-3 py-2 text-sm text-muted hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

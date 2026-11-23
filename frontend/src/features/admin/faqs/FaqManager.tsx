/**
 * Phase Admin-4 — FAQ manager.
 *
 * CRUD for FAQs with publish/unpublish. Uses the admin API client.
 */

import { useCallback, useEffect, useState } from 'react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { deleteFaq, listFaqs, updateFaq } from '../../../services/admin/adminApi.ts'
import type { Faq } from '../../../types/admin.ts'
import FaqForm from './FaqForm.tsx'
import { notification } from '../../../lib/notifications/notification.ts'

export default function FaqManager() {
  const { accessToken } = useAuth()
  const faqsQuery = useApiQuery<Faq[]>(
    ['admin', 'faqs', accessToken],
    () => listFaqs(accessToken as string),
    accessToken !== null,
  )
  // Start from cached FAQs when returning to the page, without a loading flash.
  const [faqs, setFaqs] = useState<Faq[]>(() => faqsQuery.data ?? [])
  const [isLoading, setIsLoading] = useState(() => faqsQuery.data === undefined)
  // Saves update the cached list, which the effect below copies into the page,
  // so returning to this page never shows an outdated list.
  const updateFaqs = useCallback(
    (change: (prev: Faq[]) => Faq[]) =>
      queryClient.setQueryData<Faq[]>(['admin', 'faqs', accessToken], (prev) => change(prev ?? [])),
    [accessToken],
  )
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Faq | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)

  useEffect(() => {
    if (faqsQuery.isFetching && faqsQuery.data === undefined) setIsLoading(true)
    if (faqsQuery.data) {
      setFaqs(faqsQuery.data)
      setIsLoading(false)
    }
    if (faqsQuery.isError) {
      setError(faqsQuery.error instanceof Error ? faqsQuery.error.message : 'Failed to load FAQs.')
      setIsLoading(false)
    }
  }, [faqsQuery.data, faqsQuery.error, faqsQuery.isError, faqsQuery.isFetching])

  const handleDelete = useCallback(
    async (id: string) => {
      if (accessToken === null) return
      if (!window.confirm('Delete this FAQ?')) return
      try {
        await deleteFaq(accessToken, id)
        updateFaqs((prev) => prev.filter((f) => f.faq_id !== id))
        notification.success('FAQ deleted successfully')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete FAQ.')
      }
    },
    [accessToken],
  )

  const handleToggleActive = useCallback(
    async (faq: Faq) => {
      if (accessToken === null) return
      try {
        const updated = await updateFaq(accessToken, faq.faq_id, { is_active: !faq.is_active })
        updateFaqs((prev) => prev.map((f) => (f.faq_id === updated.faq_id ? updated : f)))
        notification.success(updated.is_active ? 'FAQ published successfully' : 'FAQ unpublished successfully')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update FAQ.')
      }
    },
    [accessToken],
  )

  if (isLoading) {
    return <div className="text-muted py-8">Loading FAQs…</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-bold text-content text-section">FAQs</h2>
        <button
          type="button"
          onClick={() => {
            setEditing(null)
            setIsFormOpen(true)
          }}
          className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Add FAQ
        </button>
      </div>

      {error !== null && (
        <div role="alert" className="rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {isFormOpen && (
        <FaqForm
          initial={editing}
          onClose={() => setIsFormOpen(false)}
          onSaved={(faq) => {
            updateFaqs((prev) => {
              const exists = prev.some((f) => f.faq_id === faq.faq_id)
              return exists ? prev.map((f) => (f.faq_id === faq.faq_id ? faq : f)) : [...prev, faq]
            })
            notification.success(editing ? 'FAQ updated successfully' : 'FAQ created successfully')
            setIsFormOpen(false)
          }}
        />
      )}

      {faqs.length === 0 ? (
        <p className="text-sm text-muted">No FAQs yet.</p>
      ) : (
        <ul className="space-y-2">
          {faqs.map((faq) => (
            <li key={faq.faq_id} className="rounded-lg border border-line bg-surface px-4 py-3">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1 basis-full sm:basis-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-content break-words">{faq.question}</span>
                    {!faq.is_active && <span className="rounded bg-raised px-2 py-0.5 text-xs text-muted">draft</span>}
                  </div>
                  <p className="mt-1 text-xs text-muted line-clamp-2">{faq.answer}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleToggleActive(faq)}
                    className="rounded border border-control bg-surface px-2 py-1 text-xs text-muted hover:bg-hover"
                  >
                    {faq.is_active ? 'Unpublish' : 'Publish'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(faq)
                      setIsFormOpen(true)
                    }}
                    className="rounded border border-control bg-surface px-2 py-1 text-xs text-muted hover:bg-hover"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(faq.faq_id)}
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

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { EmptyState, Message } from './PublicChatMessages.tsx'
import { usePublicChat } from './usePublicChat.ts'
import PublicRequestFeedback from './recovery/PublicRequestFeedback.tsx'
export default function PublicChatPage({ institutionCode }: { institutionCode: string }) {
  const {
    messages,
    isLoading,
    error,
    failedMessageId,
    sendMessage,
    retry,
    stopWaiting,
    retryAfterSeconds,
    startNewConversation,
    clear,
  } = usePublicChat(institutionCode)
  const [draft, setDraft] = useState('')
  const [confirmingClear, setConfirmingClear] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const clearButtonRef = useRef<HTMLButtonElement | null>(null)
  const cancelClearRef = useRef<HTMLButtonElement | null>(null)
  const canSend = !isLoading && failedMessageId === null && draft.trim().length > 0 && draft.length <= 4000

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [messages.length, isLoading, error])

  useEffect(() => {
    if (!isLoading && !confirmingClear) inputRef.current?.focus()
  }, [confirmingClear, isLoading])

  useEffect(() => {
    if (confirmingClear) cancelClearRef.current?.focus()
  }, [confirmingClear])

  const submit = (event?: FormEvent): void => {
    event?.preventDefault()
    if (!canSend) return
    const outgoing = draft
    setDraft('')
    void sendMessage(outgoing)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  const beginNewConversation = (): void => {
    startNewConversation()
    setDraft('')
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  const closeClearConfirmation = (): void => {
    setConfirmingClear(false)
    setTimeout(() => clearButtonRef.current?.focus(), 0)
  }

  const confirmClear = (): void => {
    clear()
    setDraft('')
    setConfirmingClear(false)
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  const onClearDialogKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeClearConfirmation()
      return
    }
    if (event.key !== 'Tab') return
    const controls = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not([disabled])'))
    if (controls.length === 0) return
    const first = controls[0]
    const last = controls[controls.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <div className="min-h-[100dvh] bg-canvas text-content">
      <header className="border-b border-line bg-shell px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-3xl flex-col items-start justify-between gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.18em] text-accent">{institutionCode}</p>
            <h1 className="truncate font-bold text-content text-page">Public College AI Assistant</h1>
          </div>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:shrink-0">
            <button
              type="button"
              onClick={beginNewConversation}
              disabled={isLoading}
              className="rounded-lg px-3 py-2 text-xs font-medium text-muted hover:bg-hover hover:text-content focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
            >
              New conversation
            </button>
            {messages.length > 0 ? (
              <button
                ref={clearButtonRef}
                type="button"
                onClick={() => setConfirmingClear(true)}
                disabled={isLoading}
                className="rounded-lg px-3 py-2 text-xs font-medium text-muted hover:bg-hover hover:text-content focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
              >
                Clear conversation
              </button>
            ) : null}
            <a
              href="/login"
              className="rounded-lg border border-line px-3 py-2 text-xs font-semibold text-content hover:border-control hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Sign in
            </a>
          </div>
        </div>
      </header>

      <main className="mx-auto flex min-h-[calc(100dvh-73px)] max-w-3xl flex-col px-3 sm:px-6">
        <section className="flex-1 overflow-y-auto py-6" aria-label="Public chat conversation">
          {messages.length === 0 && !isLoading ? (
            <EmptyState onSuggestion={setDraft} />
          ) : (
            <ol className="space-y-5" role="log" aria-live="polite" aria-relevant="additions">
              {messages.map((message) => (
                <Message key={message.id} message={message} />
              ))}
            </ol>
          )}
          <PublicRequestFeedback
            loading={isLoading}
            error={error}
            canRetry={failedMessageId !== null}
            retryAfterSeconds={retryAfterSeconds}
            onRetry={() => void retry()}
            onStop={stopWaiting}
          />
          <div ref={bottomRef} aria-hidden="true" />
        </section>

        <div className="sticky bottom-0 -mx-3 border-t border-line bg-canvas px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:-mx-6 sm:px-6">
          <form onSubmit={submit} className="mx-auto max-w-3xl">
            <label htmlFor="public-chat-message" className="sr-only">
              Ask a public college question
            </label>
            <div className="flex items-end gap-2 rounded-xl border border-line bg-surface p-2 shadow-2xl shadow-black/20 focus-within:border-accent focus-within:ring-1 focus-within:ring-accent">
              <textarea
                ref={inputRef}
                id="public-chat-message"
                rows={2}
                maxLength={4000}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={onKeyDown}
                disabled={isLoading}
                placeholder="Ask about published college information…"
                className="max-h-36 min-h-12 flex-1 resize-y bg-transparent px-2 py-2 text-sm leading-6 text-content placeholder:text-muted focus:outline-none disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!canSend}
                className="min-h-11 rounded-xl bg-accent px-4 py-2 text-sm font-bold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send
              </button>
            </div>
            <div className="mt-1 flex justify-between px-1 text-xs text-muted">
              <span>Enter to send · Shift+Enter for a new line</span>
              <span aria-live="polite">{draft.length}/4000</span>
            </div>
            <p className="mt-1 px-1 text-xs text-muted">
              History is stored only in this browser for {institutionCode}.
            </p>
          </form>
        </div>
      </main>
      {confirmingClear ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="clear-conversation-title"
          aria-describedby="clear-conversation-description"
          onKeyDown={onClearDialogKeyDown}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
        >
          <div className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-2xl">
            <h2 id="clear-conversation-title" className="font-bold text-content text-section">
              Clear this conversation?
            </h2>
            <p id="clear-conversation-description" className="mt-2 text-sm leading-6 text-muted">
              This removes this college's conversation from this browser. Other colleges are not affected.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                ref={cancelClearRef}
                type="button"
                onClick={closeClearConfirmation}
                className="rounded-lg border border-line px-4 py-2 text-sm font-semibold text-content focus:outline-none focus:ring-2 focus:ring-accent"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmClear}
                className="rounded-lg bg-danger-bg px-4 py-2 text-sm font-semibold text-content focus:outline-none focus:ring-2 focus:ring-accent"
              >
                Clear conversation
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
export { PublicChatRouteError } from './PublicChatMessages.tsx'

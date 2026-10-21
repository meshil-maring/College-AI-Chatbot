import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { EmptyState, Message } from './PublicChatMessages.tsx'
import { usePublicChat } from './usePublicChat.ts'
export default function PublicChatPage({ institutionCode }: { institutionCode: string }) {
  const { messages, isLoading, error, failedMessageId, sendMessage, retry, startNewConversation, clear } =
    usePublicChat(institutionCode)
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
    <div className="min-h-[100dvh] bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
              {institutionCode}
            </p>
            <h1 className="truncate text-lg font-bold text-white sm:text-xl">Public College AI Assistant</h1>
          </div>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:shrink-0">
            <button
              type="button"
              onClick={beginNewConversation}
              disabled={isLoading}
              className="rounded-lg px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-50"
            >
              New conversation
            </button>
            {messages.length > 0 ? (
              <button
                ref={clearButtonRef}
                type="button"
                onClick={() => setConfirmingClear(true)}
                disabled={isLoading}
                className="rounded-lg px-3 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-50"
              >
                Clear conversation
              </button>
            ) : null}
            <a
              href="/login"
              className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-slate-500 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              Sign in
            </a>
          </div>
        </div>
      </header>

      <main className="mx-auto flex min-h-[calc(100dvh-73px)] max-w-5xl flex-col px-3 sm:px-6">
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
          {isLoading ? (
            <div
              className="mt-5 mr-auto flex w-fit items-center gap-2 rounded-2xl rounded-tl-md border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-slate-300"
              role="status"
            >
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" aria-hidden="true" />
              Thinking…
            </div>
          ) : null}
          {error ? (
            <div
              className="mt-5 rounded-xl border border-rose-800/70 bg-rose-950/40 p-3 text-sm text-rose-100"
              role="alert"
            >
              <p>{error}</p>
              {failedMessageId ? (
                <button
                  type="button"
                  onClick={() => void retry()}
                  className="mt-2 rounded-lg border border-rose-700 px-3 py-1.5 text-xs font-semibold hover:bg-rose-900/60 focus:outline-none focus:ring-2 focus:ring-rose-400"
                >
                  Retry
                </button>
              ) : null}
            </div>
          ) : null}
          <div ref={bottomRef} aria-hidden="true" />
        </section>

        <div className="sticky bottom-0 -mx-3 border-t border-slate-800 bg-slate-950/95 px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:-mx-6 sm:px-6">
          <form onSubmit={submit} className="mx-auto max-w-4xl">
            <label htmlFor="public-chat-message" className="sr-only">
              Ask a public college question
            </label>
            <div className="flex items-end gap-2 rounded-2xl border border-slate-700 bg-slate-900 p-2 shadow-2xl shadow-black/20 focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500">
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
                className="max-h-36 min-h-12 flex-1 resize-y bg-transparent px-2 py-2 text-sm leading-6 text-white placeholder:text-slate-500 focus:outline-none disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!canSend}
                className="min-h-11 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send
              </button>
            </div>
            <div className="mt-1 flex justify-between px-1 text-[11px] text-slate-500">
              <span>Enter to send · Shift+Enter for a new line</span>
              <span aria-live="polite">{draft.length}/4000</span>
            </div>
            <p className="mt-1 px-1 text-[11px] text-slate-600">
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
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h2 id="clear-conversation-title" className="text-lg font-bold text-white">
              Clear this conversation?
            </h2>
            <p id="clear-conversation-description" className="mt-2 text-sm leading-6 text-slate-400">
              This removes this college's conversation from this browser. Other colleges are not affected.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                ref={cancelClearRef}
                type="button"
                onClick={closeClearConfirmation}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmClear}
                className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-rose-300"
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

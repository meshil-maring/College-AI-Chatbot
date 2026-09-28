import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import type { PublicChatMessage, PublicChatSource } from '../../types/publicChat.ts'
import { usePublicChat } from './usePublicChat.ts'

function SourceList({ sources }: { sources: PublicChatSource[] }) {
  if (sources.length === 0) return null
  return (
    <section className="mt-4 border-t border-slate-700/70 pt-3" aria-label="Sources">
      <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-300">Sources</h3>
      <ul className="mt-2 space-y-2">
        {sources.map((source, index) => (
          <li key={`${source.title ?? 'source'}-${source.section ?? ''}-${index}`}>
            <article className="rounded-xl border border-slate-700 bg-slate-950/40 p-3">
              <p className="text-sm font-medium text-slate-200">
                {source.title?.trim() || 'Public college source'}
                {source.section?.trim() ? (
                  <span className="font-normal text-slate-400"> · {source.section}</span>
                ) : null}
              </p>
              <blockquote className="mt-1 break-words text-xs leading-5 text-slate-400">
                “{source.quote}”
              </blockquote>
            </article>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Message({ message }: { message: PublicChatMessage }) {
  const user = message.role === 'user'
  return (
    <li className={user ? 'ml-auto max-w-[88%] sm:max-w-[78%]' : 'mr-auto max-w-[94%] sm:max-w-[84%]'}>
      <p className={`mb-1 text-xs ${user ? 'text-right text-emerald-300' : 'text-slate-500'}`}>
        {user ? 'You' : 'College AI'}
      </p>
      <article className={user
        ? 'rounded-2xl rounded-tr-md bg-emerald-600 px-4 py-3 text-white shadow-lg shadow-emerald-950/20'
        : 'rounded-2xl rounded-tl-md border border-slate-700 bg-slate-800 px-4 py-3 text-slate-100 shadow-lg shadow-slate-950/20'}>
        <p className="whitespace-pre-wrap break-words text-sm leading-6">{message.content}</p>
        {!user && message.sources ? <SourceList sources={message.sources} /> : null}
      </article>
    </li>
  )
}

function EmptyState({ onSuggestion }: { onSuggestion: (question: string) => void }) {
  const suggestions = [
    'What programmes are described in the public college information?',
    'What admission information is available?',
    'Are there any current public notices?',
  ]
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-10 text-center sm:py-16">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-2xl" aria-hidden="true">✦</div>
      <h2 className="mt-5 text-2xl font-bold tracking-tight text-white">Ask about the college</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">
        I can help find information in the college’s published FAQs, notices, and handbooks.
        Student-specific records require sign-in.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2" aria-label="Suggested questions">
        {suggestions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSuggestion(question)}
            className="rounded-full border border-slate-700 bg-slate-800/70 px-3 py-2 text-left text-xs text-slate-300 transition hover:border-emerald-500/60 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function PublicChatPage({ institutionCode }: { institutionCode: string }) {
  const { messages, isLoading, error, failedMessageId, sendMessage, retry, clear } = usePublicChat(institutionCode)
  const [draft, setDraft] = useState('')
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const canSend = !isLoading && draft.trim().length > 0 && draft.length <= 4000

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [messages.length, isLoading, error])

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

  return (
    <div className="min-h-[100dvh] bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">{institutionCode}</p>
            <h1 className="truncate text-lg font-bold text-white sm:text-xl">Public College AI Assistant</h1>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {messages.length > 0 ? (
              <button type="button" onClick={clear} disabled={isLoading} className="rounded-lg px-3 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-50">
                Clear chat
              </button>
            ) : null}
            <a href="/" className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-slate-500 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400">
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
              {messages.map((message) => <Message key={message.id} message={message} />)}
            </ol>
          )}
          {isLoading ? (
            <div className="mt-5 mr-auto flex w-fit items-center gap-2 rounded-2xl rounded-tl-md border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-slate-300" role="status">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" aria-hidden="true" />
              Thinking…
            </div>
          ) : null}
          {error ? (
            <div className="mt-5 rounded-xl border border-rose-800/70 bg-rose-950/40 p-3 text-sm text-rose-100" role="alert">
              <p>{error}</p>
              {failedMessageId ? (
                <button type="button" onClick={() => void retry()} className="mt-2 rounded-lg border border-rose-700 px-3 py-1.5 text-xs font-semibold hover:bg-rose-900/60 focus:outline-none focus:ring-2 focus:ring-rose-400">
                  Retry
                </button>
              ) : null}
            </div>
          ) : null}
          <div ref={bottomRef} aria-hidden="true" />
        </section>

        <div className="sticky bottom-0 -mx-3 border-t border-slate-800 bg-slate-950/95 px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:-mx-6 sm:px-6">
          <form onSubmit={submit} className="mx-auto max-w-4xl">
            <label htmlFor="public-chat-message" className="sr-only">Ask a public college question</label>
            <div className="flex items-end gap-2 rounded-2xl border border-slate-700 bg-slate-900 p-2 shadow-2xl shadow-black/20 focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500">
              <textarea
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
              <button type="submit" disabled={!canSend} className="min-h-11 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:cursor-not-allowed disabled:opacity-40">
                Send
              </button>
            </div>
            <div className="mt-1 flex justify-between px-1 text-[11px] text-slate-500">
              <span>Enter to send · Shift+Enter for a new line</span>
              <span aria-live="polite">{draft.length}/4000</span>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}

export function PublicChatRouteError() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-slate-950 px-4 text-center text-slate-100">
      <div className="max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
        <h1 className="text-2xl font-bold">Public chat link incomplete</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Use the public chat link supplied by your college. It includes the public institution code.
        </p>
        <a href="/" className="mt-6 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-300">Go to sign in</a>
      </div>
    </main>
  )
}

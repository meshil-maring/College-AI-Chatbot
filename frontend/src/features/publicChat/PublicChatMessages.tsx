import { memo } from 'react'
import type { PublicChatMessage, PublicChatSource } from '../../types/publicChat.ts'
export function SourceList({ sources }: { sources: PublicChatSource[] }) {
  if (sources.length === 0) return null
  return (
    <section className="mt-4 border-t border-line pt-3" aria-label="Sources">
      <h3 className="font-semibold uppercase tracking-[0.16em] text-accent text-card">Sources</h3>
      <ul className="mt-2 space-y-2">
        {sources.map((source, index) => (
          <li key={`${source.title ?? 'source'}-${source.section ?? ''}-${index}`}>
            <article className="rounded-xl border border-line bg-canvas p-3">
              <p className="text-sm font-medium text-content">
                {source.title?.trim() || 'Public college source'}
                {source.section?.trim() ? <span className="font-normal text-muted"> · {source.section}</span> : null}
              </p>
              <blockquote className="mt-1 break-words text-xs leading-5 text-muted">“{source.quote}”</blockquote>
            </article>
          </li>
        ))}
      </ul>
    </section>
  )
}

export const Message = memo(function Message({ message }: { message: PublicChatMessage }) {
  const user = message.role === 'user'
  return (
    <li className={user ? 'ml-auto max-w-[88%] sm:max-w-[78%]' : 'mr-auto max-w-[94%] sm:max-w-[84%]'}>
      <p className={`mb-1 text-xs ${user ? 'text-right text-accent' : 'text-muted'}`}>{user ? 'You' : 'College AI'}</p>
      <article
        className={
          user
            ? 'rounded-xl rounded-tr-md border border-line bg-raised px-4 py-4 text-content'
            : 'rounded-xl rounded-tl-md border border-line bg-surface px-4 py-4 text-content'
        }
      >
        <p className="whitespace-pre-wrap break-words text-reading">{message.content}</p>
        {!user && message.sources ? <SourceList sources={message.sources} /> : null}
      </article>
    </li>
  )
})

export function EmptyState({ onSuggestion }: { onSuggestion: (question: string) => void }) {
  const suggestions = [
    'What programmes are described in the public college information?',
    'What admission information is available?',
    'Are there any current public notices?',
  ]
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-10 text-center sm:py-16">
      <div
        className="flex h-14 w-14 items-center justify-center rounded-xl border border-accent bg-raised text-2xl"
        aria-hidden="true"
      >
        ✦
      </div>
      <h2 className="mt-5 font-bold tracking-tight text-content text-section">Ask about the college</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted">
        I can help find information in the college’s published FAQs, notices, and handbooks. Student-specific records
        require sign-in.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2" aria-label="Suggested questions">
        {suggestions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSuggestion(question)}
            className="rounded-full border border-line bg-surface px-3 py-2 text-left text-xs text-muted transition hover:border-accent hover:text-content focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}

export function PublicChatRouteError() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-canvas px-4 text-center text-content">
      <div className="max-w-lg rounded-xl border border-line bg-surface p-8 shadow-none">
        <h1 className="font-bold text-page">Public chat link incomplete</h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          Use the public chat link supplied by your college. It includes the public institution code.
        </p>
        <a
          href="/"
          className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Go to platform gateway
        </a>
      </div>
    </main>
  )
}

import { memo } from 'react'
import type { PublicChatMessage, PublicChatSource } from '../../types/publicChat.ts'
export function SourceList({ sources }: { sources: PublicChatSource[] }) {
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
              <blockquote className="mt-1 break-words text-xs leading-5 text-slate-400">“{source.quote}”</blockquote>
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
      <p className={`mb-1 text-xs ${user ? 'text-right text-emerald-300' : 'text-slate-500'}`}>
        {user ? 'You' : 'College AI'}
      </p>
      <article
        className={
          user
            ? 'rounded-2xl rounded-tr-md bg-emerald-600 px-4 py-3 text-white shadow-lg shadow-emerald-950/20'
            : 'rounded-2xl rounded-tl-md border border-slate-700 bg-slate-800 px-4 py-3 text-slate-100 shadow-lg shadow-slate-950/20'
        }
      >
        <p className="whitespace-pre-wrap break-words text-sm leading-6">{message.content}</p>
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
        className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-2xl"
        aria-hidden="true"
      >
        ✦
      </div>
      <h2 className="mt-5 text-2xl font-bold tracking-tight text-white">Ask about the college</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">
        I can help find information in the college’s published FAQs, notices, and handbooks. Student-specific records
        require sign-in.
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

export function PublicChatRouteError() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-slate-950 px-4 text-center text-slate-100">
      <div className="max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
        <h1 className="text-2xl font-bold">Public chat link incomplete</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Use the public chat link supplied by your college. It includes the public institution code.
        </p>
        <a
          href="/"
          className="mt-6 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-300"
        >
          Go to platform gateway
        </a>
      </div>
    </main>
  )
}

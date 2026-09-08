/**
 * Phase 5.5 — Message bubble.
 *
 * Renders one ChatMessage. User messages are right-aligned; assistant
 * messages are left-aligned and may carry:
 *   - the answer text (plain text; no markdown renderer installed), or
 *   - the dedicated insufficient-context notice when status demands it, and
 *   - backend-provided sources, usage, and model metadata.
 *
 * The frontend never fabricates an answer: when the backend reports success
 * but answer is null, a defensive fallback string is shown instead of null.
 */

import type { ChatMessage } from './chatTypes.ts'
import InsufficientContextNotice from './InsufficientContextNotice.tsx'
import SourceCard from './SourceCard.tsx'
import UsageBadge from './UsageBadge.tsx'

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  const bubbleClass = isUser
    ? 'ml-auto rounded-2xl rounded-tr-sm border border-emerald-700 bg-emerald-900/60 px-4 py-2.5 text-sm text-slate-100 max-w-[85%]'
    : 'mr-auto rounded-2xl rounded-tl-sm border border-slate-600 bg-slate-800 px-4 py-2.5 text-sm text-slate-100 max-w-[85%]'

  const label = isUser ? 'You' : 'College AI'

  return (
    <li className="flex flex-col gap-1">
      <span className="text-[11px] text-slate-500">{label}</span>
      <div className={bubbleClass}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.status === 'insufficient_context' ? (
          <InsufficientContextNotice />
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}

        {!isUser && message.sources && message.sources.length > 0 ? (
          <ul className="mt-2 flex flex-col gap-2">
            {message.sources.map((source) => (
              <li key={source.chunk_id}>
                <SourceCard source={source} />
              </li>
            ))}
          </ul>
        ) : null}

        {!isUser ? (
          <UsageBadge
            usage={message.usage ?? null}
            modelUsed={message.modelUsed ?? null}
          />
        ) : null}
      </div>
    </li>
  )
}
/**
 * Phase 5.5 — Message list.
 *
 * Renders the chronological conversation (user / assistant / ...) and keeps
 * the latest message visible by auto-scrolling to the bottom. New messages
 * appear at the bottom. A loading indicator is shown while a request is pending.
 *
 * No server-side message history retrieval is performed: this is the active
 * in-browser session only.
 */

import { useEffect, useRef } from 'react'
import type { ChatMessage } from './chatTypes.ts'
import LoadingIndicator from './LoadingIndicator.tsx'
import MessageBubble from './MessageBubble.tsx'

export default function MessageList({
  messages,
  isLoading,
}: {
  messages: ChatMessage[]
  isLoading: boolean
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, isLoading])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex h-full items-center justify-center px-4">
        <div className="max-w-md text-center">
          <p className="text-lg font-semibold text-slate-200">
            College AI Chatbot
          </p>
          <p className="mt-2 text-sm text-slate-400">
            Ask a question about your college. For example:
          </p>
          <p className="mt-1 text-sm text-slate-400">
            “What attendance level do I need in a course to be allowed to take
            the regular end-semester exam?”
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
      className="flex flex-col gap-4"
    >
      <ol className="flex flex-col gap-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading ? (
          <li className="mr-auto">
            <div className="rounded-2xl rounded-tl-sm border border-slate-600 bg-slate-800 px-4 py-2.5">
              <LoadingIndicator />
            </div>
          </li>
        ) : null}
      </ol>
      <div ref={bottomRef} className="h-1" aria-hidden="true" />
    </div>
  )
}
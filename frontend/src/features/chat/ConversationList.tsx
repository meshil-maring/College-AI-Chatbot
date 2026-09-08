/**
 * Phase 5.7 — Conversation history list.
 *
 * Displays the authenticated user's persisted conversations in a sidebar.
 * Conversations are ordered by `updated_at` DESC (as returned by the backend).
 *
 * States:
 *   - Loading: skeleton/loading indicator
 *   - Empty: "No conversations yet" message
 *   - Error: user-safe error with retry option
 *   - Populated: list of conversations with title and updated time
 *
 * Accessibility:
 *   - Uses semantic <nav> with aria-label
 *   - Each conversation is a button with visible focus state
 *   - Selected conversation uses aria-current
 *   - Keyboard accessible (Enter/Space to select)
 */

import type { ConversationSummary } from '../../types/conversation.ts'

/** Format an ISO timestamp into a user-friendly relative/absolute string. */
function formatUpdatedAt(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMinutes < 1) {
    return 'Just now'
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`
  }
  if (diffDays < 7) {
    return `${diffDays}d ago`
  }
  // Fall back to date for older conversations
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

/** Display title for a conversation, with fallback for untitled ones. */
function displayTitle(conversation: ConversationSummary): string {
  const title = conversation.title?.trim()
  if (title && title.length > 0) {
    return title
  }
  return 'Untitled conversation'
}

interface ConversationListProps {
  conversations: ConversationSummary[]
  selectedConversationId: string | null
  isLoading: boolean
  error: string | null
  onSelect: (conversationId: string) => void
  onRetry: () => void
}

export default function ConversationList({
  conversations,
  selectedConversationId,
  isLoading,
  error,
  onSelect,
  onRetry,
}: ConversationListProps) {
  if (isLoading) {
    return (
      <nav aria-label="Conversation history" className="flex flex-col gap-2 p-3">
        <div className="h-4 w-24 animate-pulse rounded bg-slate-700" aria-hidden="true" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-slate-800" aria-hidden="true" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-slate-800" aria-hidden="true" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-slate-800" aria-hidden="true" />
        <span className="sr-only">Loading conversations…</span>
      </nav>
    )
  }

  if (error !== null) {
    return (
      <nav aria-label="Conversation history" className="flex flex-col gap-2 p-3">
        <div
          role="alert"
          className="rounded-lg border border-red-900/50 bg-red-500/10 px-3 py-2 text-xs text-red-300"
        >
          {error}
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Retry
        </button>
      </nav>
    )
  }

  if (conversations.length === 0) {
    return (
      <nav aria-label="Conversation history" className="flex flex-col gap-2 p-3">
        <p className="text-xs text-slate-400">
          No conversations yet.
          <br />
          Start a new chat.
        </p>
      </nav>
    )
  }

  return (
    <nav aria-label="Conversation history" className="flex flex-col gap-1 p-2">
      {conversations.map((conversation) => {
        const isSelected = conversation.conversation_id === selectedConversationId
        return (
          <button
            key={conversation.conversation_id}
            type="button"
            onClick={() => onSelect(conversation.conversation_id)}
            aria-current={isSelected ? 'true' : undefined}
            className={`w-full rounded-lg px-3 py-2 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-400 ${
              isSelected
                ? 'bg-emerald-900/40 border border-emerald-700'
                : 'border border-transparent hover:bg-slate-800'
            }`}
          >
            <span className="block truncate text-sm font-medium text-slate-200">
              {displayTitle(conversation)}
            </span>
            <span className="block text-[11px] text-slate-500">
              {formatUpdatedAt(conversation.updated_at)}
            </span>
          </button>
        )
      })}
    </nav>
  )
}

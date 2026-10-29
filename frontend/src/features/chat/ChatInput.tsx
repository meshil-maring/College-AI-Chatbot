/**
 * Phase 5.5 — Chat input.
 *
 * A textarea + send button. Behavior:
 *   - Enter sends; Shift+Enter inserts a newline.
 *   - Disabled while loading, while unauthenticated, or when input is blank.
 *   - Blank (whitespace-only) input never generates a request.
 *
 * No voice input, no file uploads, no unrelated features.
 */

import { useState, type KeyboardEvent } from 'react'

export default function ChatInput({
  onSend,
  disabled,
  autoFocus = false,
}: {
  onSend: (text: string) => void
  disabled: boolean
  autoFocus?: boolean
}) {
  const [value, setValue] = useState('')

  const canSubmit = !disabled && value.trim().length > 0

  const submit = () => {
    if (!canSubmit) {
      return
    }
    onSend(value.trim())
    setValue('')
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex items-end gap-2">
      <label htmlFor="chat-message-input" className="sr-only">
        Ask a question
      </label>
      <textarea
        autoFocus={autoFocus}
        id="chat-message-input"
        name="chat-message-input"
        rows={2}
        maxLength={2000}
        placeholder="Ask a question about your college…"
        aria-disabled={disabled}
        disabled={disabled}
        className="min-h-[44px] flex-1 resize-none rounded-xl border border-control bg-surface px-3 py-2 text-sm text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        onClick={submit}
        disabled={!canSubmit}
        aria-label="Send message"
        className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        Send
      </button>
    </div>
  )
}

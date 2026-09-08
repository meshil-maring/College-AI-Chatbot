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
}: {
  onSend: (text: string) => void
  disabled: boolean
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
        id="chat-message-input"
        name="chat-message-input"
        rows={2}
        maxLength={2000}
        placeholder="Ask a question about your college…"
        aria-disabled={disabled}
        disabled={disabled}
        className="min-h-[44px] flex-1 resize-none rounded-xl border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        onClick={submit}
        disabled={!canSubmit}
        aria-label="Send message"
        className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Send
      </button>
    </div>
  )
}
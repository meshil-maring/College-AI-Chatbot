import './resourceSetup.ts'
import { act, render, renderHook, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useChat } from '../../../hooks/useChat.ts'
import { restoredMessages } from '../state/chatMessages.ts'
import MessageBubble from '../MessageBubble.tsx'
import type { ChatMessage } from '../chatTypes.ts'
import type { MessageSummary } from '../../../types/conversation.ts'
import { auth, resource } from './resourceSetup.ts'

function History({ messages }: { messages: readonly ChatMessage[] }) {
  return (
    <ol>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </ol>
  )
}

const card = {
  chunk_id: 'chunk-a',
  source_title: 'Library handbook',
  section: 'Borrowing',
  quote: 'Borrow two books for seven days.',
  relevance_score: 0.85,
}
const answer: MessageSummary = {
  message_id: 'answer-a',
  conversation_id: 'conversation-a',
  message_sequence: 2,
  message_type: 'assistant',
  content_text: 'You may borrow **two books**.',
  created_at: '2026-10-29T00:00:00Z',
  sources: [card],
}

describe('saved citation cards', () => {
  it('restores the server source fields and shared card UI with formatted history', () => {
    const { result, rerender } = renderHook(() => useChat(resource))
    act(() => result.current.loadConversation('conversation-a', [answer], resource))
    expect(result.current.messages[0].sources).toEqual([card])
    render(<History messages={result.current.messages} />)
    expect(screen.getByText('Library handbook', { exact: false })).toBeVisible()
    expect(screen.getByText('Borrowing', { exact: false })).toBeVisible()
    expect(screen.getByText('Relevance 85%')).toBeVisible()
    expect(screen.getByText(/Borrow two books for seven days/)).toBeVisible()
    expect(screen.getByText('two books').tagName).toBe('STRONG')
    auth.accessToken = 'renewed-token'
    rerender()
    expect(result.current.messages[0].sources).toEqual([card])
  })

  it('removes old citation content on selection and renders a redacted history without cards', () => {
    const { result } = renderHook(() => useChat(resource))
    act(() => result.current.loadConversation('conversation-a', [answer], resource))
    const view = render(<History messages={result.current.messages} />)
    act(() => result.current.loadConversation('other', [], null))
    view.rerender(<History messages={result.current.messages} />)
    expect(screen.queryByText('Library handbook', { exact: false })).not.toBeInTheDocument()
    act(() =>
      result.current.loadConversation(
        'conversation-a',
        [
          {
            ...answer,
            content_text:
              'This part of the conversation is unavailable because source access changed. Start a new chat.',
            sources: [],
          },
        ],
        { ...resource, title: null, available: false },
      ),
    )
    view.rerender(<History messages={result.current.messages} />)
    expect(screen.queryByText(/Borrow two books for seven days/)).not.toBeInTheDocument()
    expect(result.current.messages[0].sources).toEqual([])
  })

  it('keeps older responses compatible and ignores sources attached to user messages', () => {
    const messages = restoredMessages([
      { ...answer, sources: undefined },
      { ...answer, message_id: 'question-a', message_type: 'user' },
    ])
    expect(messages[0].sources).toEqual([])
    expect(messages[1].sources).toBeUndefined()
    render(<History messages={messages} />)
    expect(screen.queryByText('Library handbook', { exact: false })).not.toBeInTheDocument()
  })
})

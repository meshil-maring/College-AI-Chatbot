/**
 * Phase 5.7 — ConversationList component tests.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConversationList from './ConversationList.tsx'
import type { ConversationSummary } from '../../types/conversation.ts'

const mockConversations: ConversationSummary[] = [
  {
    conversation_id: '12345678-1234-1234-1234-123456789abc',
    title: 'First conversation',
    status: 'active',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    conversation_id: 'aaaaaaaa-1111-2222-3333-444444444444',
    title: null,
    status: 'active',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: new Date(Date.now() - 86400000).toISOString(),
  },
]

describe('ConversationList', () => {
  it('shows loading state', () => {
    render(
      <ConversationList
        conversations={[]}
        selectedConversationId={null}
        isLoading={true}
        error={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByText('Loading conversations…')).toBeInTheDocument()
  })

  it('shows empty state', () => {
    render(
      <ConversationList
        conversations={[]}
        selectedConversationId={null}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByText(/No conversations yet/)).toBeInTheDocument()
    expect(screen.getByText(/Start a new chat/)).toBeInTheDocument()
  })

  it('shows error state with retry button', () => {
    const onRetry = vi.fn()
    render(
      <ConversationList
        conversations={[]}
        selectedConversationId={null}
        isLoading={false}
        error="Something went wrong"
        onSelect={vi.fn()}
        onRetry={onRetry}
      />,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  it('calls retry when retry button is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(
      <ConversationList
        conversations={[]}
        selectedConversationId={null}
        isLoading={false}
        error="Error"
        onSelect={vi.fn()}
        onRetry={onRetry}
      />,
    )
    await user.click(screen.getByText('Retry'))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders conversation titles', () => {
    render(
      <ConversationList
        conversations={mockConversations}
        selectedConversationId={null}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByText('First conversation')).toBeInTheDocument()
    expect(screen.getByText('Untitled conversation')).toBeInTheDocument()
  })

  it('calls onSelect when a conversation is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <ConversationList
        conversations={mockConversations}
        selectedConversationId={null}
        isLoading={false}
        error={null}
        onSelect={onSelect}
        onRetry={vi.fn()}
      />,
    )
    await user.click(screen.getByText('First conversation'))
    expect(onSelect).toHaveBeenCalledWith('12345678-1234-1234-1234-123456789abc')
  })

  it('marks selected conversation with aria-current', () => {
    render(
      <ConversationList
        conversations={mockConversations}
        selectedConversationId="12345678-1234-1234-1234-123456789abc"
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    const buttons = screen.getAllByRole('button')
    const selectedButton = buttons.find(
      (btn) => btn.getAttribute('aria-current') === 'true',
    )
    expect(selectedButton).toBeDefined()
    expect(selectedButton).toHaveTextContent('First conversation')
  })

  it('has accessible nav label', () => {
    render(
      <ConversationList
        conversations={mockConversations}
        selectedConversationId={null}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByRole('navigation', { name: /Conversation history/ })).toBeInTheDocument()
  })
})

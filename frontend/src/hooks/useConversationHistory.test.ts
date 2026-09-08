/**
 * Phase 5.7 — useConversationHistory hook tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useConversationHistory } from './useConversationHistory.ts'
import { ApiError } from '../services/api.ts'

vi.mock('../services/api.ts', () => ({
  ApiError: class extends Error {
    status: number
    details: unknown
    constructor(status: number, message: string, details?: unknown) {
      super(message)
      this.name = 'ApiError'
      this.status = status
      this.details = details
    }
  },
  listConversations: vi.fn(),
  getConversationMessages: vi.fn(),
}))

import { getConversationMessages, listConversations } from '../services/api.ts'

describe('useConversationHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts with empty conversations and no selection', () => {
    const { result } = renderHook(() => useConversationHistory())
    expect(result.current.conversations).toEqual([])
    expect(result.current.selectedConversationId).toBeNull()
    expect(result.current.historyLoading).toBe(false)
    expect(result.current.historyError).toBeNull()
  })

  it('loads conversations and handles empty list', async () => {
    vi.mocked(listConversations).mockResolvedValueOnce([])
    const { result } = renderHook(() => useConversationHistory())
    await act(async () => {
      await result.current.loadConversations('test-token')
    })
    expect(result.current.conversations).toEqual([])
    expect(result.current.historyError).toBeNull()
    expect(result.current.historyLoading).toBe(false)
  })

  it('handles 401 and network errors', async () => {
    vi.mocked(listConversations).mockRejectedValueOnce(new ApiError(401, 'Unauthorized'))
    const { result } = renderHook(() => useConversationHistory())
    await act(async () => {
      await result.current.loadConversations('invalid-token')
    })
    expect(result.current.historyError).toBe(
      'Your session has expired or is no longer valid. Please sign out and sign in again.',
    )
  })

  it('selects a conversation and loads its messages', async () => {
    const mockMessages = [
      { message_id: 'msg-1', conversation_id: 'conv-1', message_sequence: 1, message_type: 'user', content_text: 'Hello', created_at: '2025-01-01T00:00:00Z' },
    ]
    vi.mocked(getConversationMessages).mockResolvedValueOnce(mockMessages)
    const { result } = renderHook(() => useConversationHistory())
    let messages: unknown[] = []
    await act(async () => {
      messages = await result.current.selectConversation('conv-1', 'test-token')
    })
    expect(result.current.selectedConversationId).toBe('conv-1')
    expect(messages).toEqual(mockMessages)
    expect(result.current.messagesError).toBeNull()
  })

  it('handles 404 when selecting clears selection', async () => {
    vi.mocked(getConversationMessages).mockRejectedValueOnce(new ApiError(404, 'Not found'))
    const { result } = renderHook(() => useConversationHistory())
    await act(async () => {
      try {
        await result.current.selectConversation('nonexistent', 'test-token')
      } catch { /* Expected */ }
    })
    expect(result.current.selectedConversationId).toBeNull()
    expect(result.current.messagesError).toBe(
      'The selected conversation could not be found. It may have been removed.',
    )
  })

  it('clears selection and all state', async () => {
    vi.mocked(getConversationMessages).mockResolvedValueOnce([])
    const { result } = renderHook(() => useConversationHistory())
    await act(async () => {
      await result.current.selectConversation('conv-1', 'test-token')
    })
    expect(result.current.selectedConversationId).toBe('conv-1')
    act(() => { result.current.clearSelection() })
    expect(result.current.selectedConversationId).toBeNull()
    act(() => { result.current.clearAll() })
    expect(result.current.conversations).toEqual([])
  })
})

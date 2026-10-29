import './resourceSetup.ts'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/chat/api.ts'
import * as recovery from '../../../services/chat/recovery.ts'
import type { ChatRequest } from '../../../types/chat.ts'
import { useChat } from '../../../hooks/useChat.ts'
import { auth, reply, resource } from './resourceSetup.ts'

vi.mock('../../../services/chat/recovery.ts', async (original) => ({
  ...(await original<typeof import('../../../services/chat/recovery.ts')>()),
  getChatTurn: vi.fn(),
}))

function status(request: ChatRequest, state: 'processing' | 'failed' | 'completed', response = reply()) {
  return {
    turn_id: request.turn_id!,
    conversation_id: 'conversation-a',
    state,
    retryable: state === 'failed',
    retry_after_seconds: state === 'processing' ? 10 : 0,
    request: { ...request, conversation_id: 'conversation-a' },
    response: state === 'completed' ? response : null,
  }
}
beforeEach(() => vi.mocked(recovery.getChatTurn).mockReset())

describe('durable reply recovery', () => {
  it('recovers a saved reply without another POST or another question', async () => {
    vi.mocked(api.chat).mockRejectedValueOnce(new TypeError('Connection lost'))
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Hostel rules?')
    })
    const request = vi.mocked(api.chat).mock.calls[0][0]
    expect(request.turn_id).toMatch(/^[\da-f-]{36}$/)
    expect(request.session_id).toMatch(/^[\da-f-]{36}$/)
    expect(result.current.messages).toHaveLength(1)
    vi.mocked(recovery.getChatTurn).mockResolvedValueOnce(status(request, 'completed'))
    await act(async () => {
      await result.current.checkReply()
    })
    expect(api.chat).toHaveBeenCalledTimes(1)
    expect(result.current.messages).toHaveLength(2)
    expect(result.current.recovery).toBeNull()
  })

  it('retries a failed turn with its original ID and preserves one question', async () => {
    vi.mocked(api.chat).mockRejectedValueOnce(new api.ApiError(503, 'Provider unavailable'))
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Hostel rules?')
    })
    const request = vi.mocked(api.chat).mock.calls[0][0]
    vi.mocked(recovery.getChatTurn).mockResolvedValueOnce(status(request, 'failed'))
    await act(async () => {
      await result.current.checkReply()
    })
    expect(result.current.recovery?.retryable).toBe(true)
    await act(async () => {
      await Promise.all([result.current.retryReply(), result.current.retryReply()])
    })
    expect(api.chat).toHaveBeenCalledTimes(2)
    expect(vi.mocked(api.chat).mock.calls[1][0]).toEqual(
      expect.objectContaining({
        turn_id: request.turn_id,
        user_query: request.user_query,
        session_id: request.session_id,
      }),
    )
    expect(result.current.messages.filter((message) => message.role === 'user')).toHaveLength(1)
    expect(result.current.messages).toHaveLength(2)
  })

  it('checks a running turn without enabling another write', async () => {
    vi.mocked(api.chat).mockRejectedValueOnce(new TypeError('Connection lost'))
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    const request = vi.mocked(api.chat).mock.calls[0][0]
    vi.mocked(recovery.getChatTurn).mockResolvedValueOnce(status(request, 'processing'))
    await act(async () => {
      await result.current.checkReply()
      await result.current.retryReply()
      await result.current.sendMessage('Another question')
    })
    expect(result.current.recovery?.retryable).toBe(false)
    expect(api.chat).toHaveBeenCalledTimes(1)
  })

  it('retains the request through token renewal and checks with the current token', async () => {
    vi.mocked(api.chat).mockRejectedValueOnce(new TypeError('Connection lost'))
    const { result, rerender } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    const request = vi.mocked(api.chat).mock.calls[0][0]
    auth.accessToken = 'renewed-token'
    rerender()
    vi.mocked(recovery.getChatTurn).mockResolvedValueOnce(status(request, 'completed'))
    await act(async () => {
      await result.current.checkReply()
    })
    expect(recovery.getChatTurn).toHaveBeenCalledWith(request.turn_id, 'renewed-token', expect.any(AbortSignal))
  })

  it('does not display a recovered reply after selection changes', async () => {
    vi.mocked(api.chat).mockRejectedValueOnce(new TypeError('Connection lost'))
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    const request = vi.mocked(api.chat).mock.calls[0][0]
    let resolve!: (value: ReturnType<typeof status>) => void
    vi.mocked(recovery.getChatTurn).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    let check!: Promise<void>
    act(() => {
      check = result.current.checkReply()
    })
    act(() => result.current.loadConversation('other', [], { ...resource, knowledge_source_id: 'other-source' }))
    await act(async () => {
      resolve(status(request, 'completed'))
      await check
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.conversationId).toBe('other')
  })

  it('clears private content when a recovery check reports revoked access', async () => {
    vi.mocked(api.chat).mockRejectedValueOnce(new TypeError('Connection lost'))
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    vi.mocked(recovery.getChatTurn).mockRejectedValueOnce(new api.ApiError(409, 'Access changed'))
    await act(async () => {
      await result.current.checkReply()
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.resourceContext?.title).toBeNull()
    expect(result.current.blocked).toBe(true)
  })

  it('restores an unfinished turn from history without repeating an already saved answer', async () => {
    const response = reply()
    const request = {
      user_query: 'Question',
      turn_id: 'pending-a',
      institution_id: 'college-a',
      resource_id: 'source-a',
    }
    vi.mocked(recovery.getChatTurn).mockResolvedValueOnce(status(request, 'completed', response))
    const { result } = renderHook(() => useChat(resource))
    act(() =>
      result.current.loadConversation(
        'conversation-a',
        [
          {
            message_id: 'question-id',
            conversation_id: 'conversation-a',
            message_sequence: 1,
            message_type: 'user',
            content_text: 'Question',
            created_at: '2026-10-29T00:00:00Z',
          },
          {
            message_id: response.message_id,
            conversation_id: 'conversation-a',
            message_sequence: 2,
            message_type: 'assistant',
            content_text: response.answer,
            created_at: '2026-10-29T00:00:00Z',
          },
        ],
        resource,
        'pending-a',
      ),
    )
    await waitFor(() => expect(result.current.recovery).toBeNull())
    expect(result.current.messages).toHaveLength(2)
    expect(api.chat).not.toHaveBeenCalled()
  })
})

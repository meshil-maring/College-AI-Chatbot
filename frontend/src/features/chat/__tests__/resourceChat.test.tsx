import './resourceSetup.ts'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/chat/api.ts'
import { useChat } from '../../../hooks/useChat.ts'
import { auth, reply, resource } from './resourceSetup.ts'

describe('resource conversation state', () => {
  it('sends the selected resource on first questions and follow-ups', async () => {
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('What is the limit?')
    })
    await act(async () => {
      await result.current.sendMessage('And the period?')
    })
    expect(api.chat).toHaveBeenLastCalledWith(
      expect.objectContaining({
        resource_id: 'source-a',
        conversation_id: 'conversation-a',
        institution_id: 'college-a',
      }),
      'private-token',
    )
    expect(result.current.resourceContext?.title).toBe('Library guide')
  })
  it('restores the server-owned resource context before continuing a conversation', async () => {
    const { result } = renderHook(() => useChat())
    act(() => result.current.loadConversation('saved-a', [], resource))
    await act(async () => {
      await result.current.sendMessage('Continue')
    })
    expect(api.chat).toHaveBeenCalledWith(
      expect.objectContaining({ resource_id: 'source-a', conversation_id: 'saved-a' }),
      'private-token',
    )
  })
  it('rejects missing or changed response scope instead of displaying an unscoped answer', async () => {
    vi.mocked(api.chat).mockResolvedValueOnce({ ...reply(), resource_context: null })
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.blocked).toBe(true)
    expect(result.current.resourceContext).toEqual({ ...resource, title: null, available: false })
    await act(async () => {
      await result.current.sendMessage('Again')
    })
    expect(api.chat).toHaveBeenCalledTimes(1)
    act(() => result.current.resetChat())
    expect(result.current.resourceContext?.available).toBe(false)
  })
  it('clears stale messages and source titles when access is revoked', async () => {
    const { result } = renderHook(() => useChat(resource))
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    vi.mocked(api.chat).mockRejectedValueOnce(new api.ApiError(409, 'Changed'))
    await act(async () => {
      await result.current.sendMessage('Continue')
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.error).toContain('start a new chat')
    expect(result.current.resourceContext?.title).toBeNull()
  })
  it('ignores late replies after identity replacement', async () => {
    let resolve!: (value: ReturnType<typeof reply>) => void
    vi.mocked(api.chat).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const { result, rerender } = renderHook(() => useChat(resource))
    let request!: Promise<void>
    act(() => {
      request = result.current.sendMessage('Old question')
    })
    auth.user.user_id = 'user-b'
    auth.sessionGeneration += 1
    rerender()
    await act(async () => {
      resolve(reply())
      await request
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.conversationId).toBeNull()
  })
  it('ignores late replies after selecting a different saved conversation', async () => {
    let resolve!: (value: ReturnType<typeof reply>) => void
    vi.mocked(api.chat).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const { result } = renderHook(() => useChat(resource))
    let request!: Promise<void>
    act(() => {
      request = result.current.sendMessage('Old question')
    })
    act(() => result.current.loadConversation('other', [], { ...resource, knowledge_source_id: 'source-b' }))
    await act(async () => {
      resolve(reply())
      await request
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.conversationId).toBe('other')
  })
  it('keeps scope through token renewal and blocks synchronous duplicate sends', async () => {
    const { result, rerender } = renderHook(() => useChat(resource))
    await act(async () => {
      await Promise.all([result.current.sendMessage('Question'), result.current.sendMessage('Duplicate')])
    })
    expect(api.chat).toHaveBeenCalledTimes(1)
    auth.accessToken = 'renewed-token'
    rerender()
    await act(async () => {
      await result.current.sendMessage('Follow-up')
    })
    expect(api.chat).toHaveBeenLastCalledWith(expect.objectContaining({ resource_id: 'source-a' }), 'renewed-token')
    expect(result.current.messages).toHaveLength(4)
  })
})

import './resourceSetup.ts'
import { act, renderHook, waitFor } from '@testing-library/react'
import { StrictMode, useEffect } from 'react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/chat/api.ts'
import { useConversationHistory } from '../../../hooks/useConversationHistory.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import { resource } from './resourceSetup.ts'

const summary = {
  conversation_id: 'conversation-a',
  title: 'Private resource chat',
  status: 'active',
  created_at: '',
  updated_at: '',
  resource_context: resource,
}

describe('resource conversation history boundaries', () => {
  it('ignores cancelled initial reads during StrictMode effect replay', async () => {
    vi.mocked(api.listConversations).mockResolvedValue([summary])
    const { result } = renderHook(
      () => {
        const history = useConversationHistory('strict-identity')
        useEffect(() => {
          void history.loadConversations('private-token')
        }, [history.loadConversations])
        return history
      },
      { wrapper: StrictMode },
    )
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))
    expect(result.current.historyError).toBeNull()
  })
  it('keeps credentials out of query keys and hides cached titles after denied refresh', async () => {
    vi.mocked(api.listConversations).mockResolvedValueOnce([summary])
    const { result } = renderHook(() => useConversationHistory('identity-a'))
    await act(async () => {
      await result.current.loadConversations('private-token')
    })
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))
    expect(
      JSON.stringify(
        queryClient
          .getQueryCache()
          .getAll()
          .map((query) => query.queryKey),
      ),
    ).not.toContain('private-token')
    vi.mocked(api.listConversations).mockRejectedValueOnce(new api.ApiError(403, 'Denied'))
    await act(async () => {
      await result.current.loadConversations('private-token')
    })
    expect(result.current.conversations).toEqual([])
    expect(result.current.historyError).toContain('permission')
  })
  it('retires late list responses when the authenticated scope changes', async () => {
    let resolve!: (value: (typeof summary)[]) => void
    vi.mocked(api.listConversations).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const { result, rerender } = renderHook(({ scope }) => useConversationHistory(scope), {
      initialProps: { scope: 'identity-a' },
    })
    let request!: Promise<void>
    act(() => {
      request = result.current.loadConversations('private-token')
    })
    rerender({ scope: 'identity-b' })
    await act(async () => {
      resolve([summary])
      await request
    })
    expect(result.current.conversations).toEqual([])
    expect(queryClient.getQueryData(['conversations', 'identity-a'])).toBeUndefined()
  })
  it('does not restore a pending selection after the user starts a new chat', async () => {
    let resolve!: (value: []) => void
    vi.mocked(api.getConversationMessages).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const { result } = renderHook(() => useConversationHistory('identity-a'))
    let request!: Promise<unknown>
    act(() => {
      request = result.current.selectConversation('conversation-a', 'private-token').catch((error) => error)
    })
    act(() => result.current.clearSelection())
    await act(async () => {
      resolve([])
    })
    expect(await request).toBeInstanceOf(Error)
    expect(result.current.selectedConversationId).toBeNull()
    expect(result.current.messagesError).toBeNull()
  })
})

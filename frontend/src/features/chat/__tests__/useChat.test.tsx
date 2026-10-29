import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  auth: {
    accessToken: 'opaque-token',
    sessionGeneration: 7,
    user: { user_id: 'reader-a', institution_id: 'college-b' as string | null },
  },
  chat: vi.fn(),
}))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => mocks.auth }))
vi.mock('../../../services/chat/api.ts', async (original) => ({
  ...(await original<typeof import('../../../services/chat/api.ts')>()),
  chat: mocks.chat,
}))

import { useChat } from '../../../hooks/useChat.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import { ApiError } from '../../../services/chat/api.ts'

describe('authenticated chat institution scope', () => {
  beforeEach(() => {
    queryClient.clear()
    mocks.chat.mockReset()
    mocks.auth.user.institution_id = 'college-b'
    mocks.chat.mockResolvedValue({
      session_id: 'session',
      conversation_id: 'conversation',
      message_id: 'message',
      answer: 'Answer',
      status: 'success',
      sources: [],
      source_references: [],
    })
  })

  it('sends the authenticated institution and keeps credentials out of mutation keys', async () => {
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Where is the library?')
    })
    expect(mocks.chat).toHaveBeenCalledWith(expect.objectContaining({ institution_id: 'college-b' }), 'opaque-token')
    expect(
      JSON.stringify(
        queryClient
          .getMutationCache()
          .getAll()
          .map((mutation) => mutation.options.mutationKey),
      ),
    ).not.toContain('opaque-token')
  })

  it('does not send a question without institution scope', async () => {
    mocks.auth.user.institution_id = null
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    expect(mocks.chat).not.toHaveBeenCalled()
    expect(result.current.error).toContain('institution')
  })

  it('explains that a revoked conversation needs a new chat', async () => {
    mocks.chat.mockRejectedValue(new ApiError(409, 'Source access changed'))
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Continue')
    })
    await waitFor(() => expect(result.current.error).toContain('start a new chat'))
  })
})

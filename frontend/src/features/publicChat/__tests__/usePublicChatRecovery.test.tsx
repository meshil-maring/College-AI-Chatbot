import './PublicChatPage.support.tsx'
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { usePublicChat } from '../usePublicChat.ts'
import { publicChat, PublicChatError } from '../../../services/chat/publicChat.ts'
import { queryClient } from '../../../lib/queryClient.ts'

beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  vi.mocked(publicChat).mockReset()
})
afterEach(() => queryClient.clear())

it('ignores an old failure after leaving and returning to the same college', async () => {
  let failOld!: (reason: unknown) => void
  vi.mocked(publicChat).mockImplementationOnce(
    () =>
      new Promise((_resolve, reject) => {
        failOld = reject
      }),
  )
  const { result, rerender } = renderHook(({ code }) => usePublicChat(code), { initialProps: { code: 'GIT' } })
  let oldRequest!: Promise<void>
  act(() => {
    oldRequest = result.current.sendMessage('Original question')
  })
  rerender({ code: 'OTHER' })
  rerender({ code: 'GIT' })
  vi.mocked(publicChat).mockResolvedValueOnce({ answer: 'Current reply', status: 'success', sources: [] })
  await act(async () => result.current.retry())
  await act(async () => {
    failOld(new PublicChatError('network'))
    await oldRequest
  })
  expect(result.current.error).toBeNull()
  expect(result.current.failedMessageId).toBeNull()
  expect(result.current.messages.map((message) => message.content)).toEqual(['Original question', 'Current reply'])
})

import './PublicChatPage.support.tsx'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../../../App.tsx'
import { publicChat, PublicChatError } from '../../../services/chat/publicChat.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import type { PublicChatResponse } from '../../../types/publicChat.ts'

const answer = { answer: 'Public library hours.', status: 'success', sources: [] } as const
beforeEach(() => {
  localStorage.clear()
  queryClient.clear()
  vi.mocked(publicChat).mockReset()
  window.history.replaceState({}, '', '/public-chat/GIT')
})
afterEach(() => {
  vi.useRealTimers()
  queryClient.clear()
  window.history.replaceState({}, '', '/')
})

async function submit(text = 'When does the library open?') {
  await act(async () => {
    const input = screen.getByLabelText('Ask a public college question')
    fireEvent.change(input, { target: { value: text } })
    fireEvent.keyDown(input, { key: 'Enter' })
  })
}

describe('public reply recovery', () => {
  it('retains a timed-out question across reload and retries once without another user bubble', async () => {
    vi.mocked(publicChat).mockRejectedValueOnce(new PublicChatError('timeout'))
    const view = render(<App />)
    await submit()
    expect(screen.getByRole('alert')).toHaveTextContent('took too long')
    expect(publicChat).toHaveBeenCalledTimes(1)
    view.unmount()
    render(<App />)
    expect(screen.getByRole('alert')).toHaveTextContent('previous request was interrupted')
    vi.mocked(publicChat).mockResolvedValueOnce({ ...answer, sources: [] })
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Retry' })))
    expect(await screen.findByText(answer.answer)).toBeVisible()
    expect(screen.getAllByText('When does the library open?')).toHaveLength(1)
    expect(publicChat).toHaveBeenCalledTimes(2)
  })

  it('respects server retry delays and never resends automatically when the countdown ends', async () => {
    vi.useFakeTimers()
    vi.mocked(publicChat).mockRejectedValueOnce(new PublicChatError('busy', 429, 2))
    render(<App />)
    await submit()
    const retry = screen.getByRole('button', { name: 'Retry in 2s' })
    expect(retry).toBeDisabled()
    fireEvent.click(retry)
    expect(publicChat).toHaveBeenCalledTimes(1)
    await act(async () => vi.advanceTimersByTimeAsync(2000))
    expect(screen.getByRole('button', { name: 'Retry' })).toBeEnabled()
    expect(publicChat).toHaveBeenCalledTimes(1)
    vi.mocked(publicChat).mockResolvedValueOnce({ ...answer, sources: [] })
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Retry' })))
    expect(publicChat).toHaveBeenCalledTimes(2)
    expect(screen.getAllByText('When does the library open?')).toHaveLength(1)
  })

  it('stops waiting, preserves the question, and ignores the old reply after a successful retry', async () => {
    let finishOld!: (response: PublicChatResponse) => void
    let signal: AbortSignal | undefined
    vi.mocked(publicChat).mockImplementationOnce((_request, options) => {
      signal = typeof options === 'number' ? undefined : options?.signal
      return new Promise((resolve) => {
        finishOld = resolve
      })
    })
    render(<App />)
    await submit()
    fireEvent.click(screen.getByRole('button', { name: 'Stop waiting' }))
    expect(signal?.aborted).toBe(true)
    expect(screen.getByRole('alert')).toHaveTextContent('Your question is saved')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    vi.mocked(publicChat).mockResolvedValueOnce({ ...answer, sources: [] })
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Retry' })))
    await act(async () => finishOld({ answer: 'Late reply that must stay hidden.', status: 'success', sources: [] }))
    expect(screen.queryByText('Late reply that must stay hidden.')).not.toBeInTheDocument()
    expect(screen.getAllByText(answer.answer)).toHaveLength(1)
    expect(screen.getAllByText('When does the library open?')).toHaveLength(1)
  })

  it('discards an unsent draft when switching colleges', async () => {
    render(<App />)
    fireEvent.change(screen.getByLabelText('Ask a public college question'), { target: { value: 'Draft for GIT' } })
    await act(async () => {
      window.history.pushState({}, '', '/public-chat/OTHER')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    await waitFor(() => expect(screen.getByText('OTHER')).toBeVisible())
    expect(screen.getByLabelText('Ask a public college question')).toHaveValue('')
    expect(publicChat).not.toHaveBeenCalled()
  })
})

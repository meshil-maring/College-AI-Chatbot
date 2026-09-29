import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../../App.tsx'
import { publicChat } from '../../services/publicChat.ts'
import { publicChatStorageKey, writePublicChatHistory } from './publicChatStorage.ts'

vi.mock('../../services/publicChat.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../services/publicChat.ts')>()
  return { ...actual, publicChat: vi.fn() }
})

const authProviderSpy = vi.fn(({ children }: { children: React.ReactNode }) => <>{children}</>)
vi.mock('../auth/AuthProvider.tsx', () => ({
  AuthProvider: (props: { children: React.ReactNode }) => authProviderSpy(props),
  useAuth: () => { throw new Error('Public chat must not use authentication') },
}))

vi.mock('../../services/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

describe('public chat route and conversation', () => {
  beforeEach(() => {
    localStorage.clear()
    authProviderSpy.mockClear()
    vi.mocked(publicChat).mockReset()
    window.history.replaceState({}, '', '/public-chat/GIT')
  })

  afterEach(() => window.history.replaceState({}, '', '/'))

  it('renders on direct navigation outside AuthProvider and authenticated shells', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Public College AI Assistant' })).toBeInTheDocument()
    expect(screen.getByText('GIT')).toBeInTheDocument()
    expect(authProviderSpy).not.toHaveBeenCalled()
    expect(screen.queryByRole('navigation', { name: /student|admin|staff|faculty/i })).not.toBeInTheDocument()
  })

  it('renders user/assistant messages and safe sources as text', async () => {
    vi.mocked(publicChat).mockResolvedValueOnce({
      answer: '<script>alert(1)</script> Admissions are described in the handbook.',
      status: 'success',
      sources: [{ title: 'Academic Handbook', section: 'Admissions', quote: 'See the published admission rules.' }],
    })
    render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'What are the admission rules?')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('What are the admission rules?')).toBeInTheDocument()
    expect(await screen.findByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument()
    expect(screen.getByText('Academic Handbook')).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/provider|document_id|chunk_id/i)
  })

  it('shows loading, prevents duplicate submission, and retries without duplicating the user message', async () => {
    let rejectRequest: ((reason: Error) => void) | undefined
    vi.mocked(publicChat).mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRequest = reject }))
    render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'When are applications open?')
    fireEvent.keyDown(input, { key: 'Enter' })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getByText('Thinking…')).toBeInTheDocument()
    expect(publicChat).toHaveBeenCalledTimes(1)

    rejectRequest?.(new TypeError('network details'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
    vi.mocked(publicChat).mockResolvedValueOnce({ answer: 'June.', status: 'success', sources: [] })
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('June.')).toBeInTheDocument()
    expect(screen.getAllByText('When are applications open?')).toHaveLength(1)
    expect(screen.queryByRole('heading', { name: 'Sources' })).not.toBeInTheDocument()
  })

  it.each([429, 503])('handles overload %s safely and retries only after user action', async (status) => {
    vi.mocked(publicChat).mockRejectedValueOnce(new (await import('../../services/publicChat.ts')).PublicChatError('busy', status))
    render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'When are applications open?{enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The chatbot is busy right now. Please try again shortly.',
    )
    expect(publicChat).toHaveBeenCalledTimes(1)
    expect(screen.getAllByText('When are applications open?')).toHaveLength(1)
    expect(screen.queryByText('Thinking…')).not.toBeInTheDocument()

    vi.mocked(publicChat).mockResolvedValueOnce({ answer: 'Applications open in June.', status: 'success', sources: [] })
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Applications open in June.')).toBeInTheDocument()
    expect(screen.getAllByText('When are applications open?')).toHaveLength(1)
    expect(publicChat).toHaveBeenCalledTimes(2)
  })

  it('supports Enter-to-send and restores local history after remount', async () => {
    vi.mocked(publicChat).mockResolvedValueOnce({ answer: 'A public notice.', status: 'success', sources: [] })
    const view = render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'Any notices?{enter}')
    expect(await screen.findByText('A public notice.')).toBeInTheDocument()
    await waitFor(() => expect(localStorage.length).toBe(1))
    view.unmount()
    render(<App />)
    expect(screen.getByText('Any notices?')).toBeInTheDocument()
    expect(screen.getByText('A public notice.')).toBeInTheDocument()
  })

  it('preserves deterministic ordering across multiple turns', async () => {
    vi.mocked(publicChat)
      .mockResolvedValueOnce({ answer: 'Answer one.', status: 'success', sources: [] })
      .mockResolvedValueOnce({ answer: 'javascript:alert(1)', status: 'success', sources: [] })
    render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'Question one{enter}')
    await screen.findByText('Answer one.')
    await userEvent.type(input, 'Question two{enter}')
    await screen.findByText('javascript:alert(1)')

    const transcript = screen.getByRole('log').textContent ?? ''
    expect(transcript.indexOf('Question one')).toBeLessThan(transcript.indexOf('Answer one.'))
    expect(transcript.indexOf('Answer one.')).toBeLessThan(transcript.indexOf('Question two'))
    expect(transcript.indexOf('Question two')).toBeLessThan(transcript.indexOf('javascript:alert(1)'))
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull()
  })

  it('starts a new conversation and clears only the current institution after confirmation', async () => {
    writePublicChatHistory('OTHER', [
      { id: 'other-u', role: 'user', content: 'Other college question', createdAt: 1 },
      { id: 'other-a', role: 'assistant', content: 'Other answer', createdAt: 2 },
    ])
    vi.mocked(publicChat).mockResolvedValue({ answer: 'Current answer', status: 'success', sources: [] })
    render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'Current question{enter}')
    await screen.findByText('Current answer')

    await userEvent.click(screen.getByRole('button', { name: 'New conversation' }))
    expect(screen.queryByText('Current question')).not.toBeInTheDocument()
    expect(localStorage.getItem(publicChatStorageKey('GIT'))).toBeNull()

    await userEvent.type(input, 'Question to clear{enter}')
    await screen.findByText('Current answer')
    const clearTrigger = screen.getByRole('button', { name: 'Clear conversation' })
    await userEvent.click(clearTrigger)
    const dialog = screen.getByRole('dialog', { name: 'Clear this conversation?' })
    const cancelButton = screen.getByRole('button', { name: 'Cancel' })
    const confirmButton = within(dialog).getByRole('button', { name: 'Clear conversation' })
    expect(cancelButton).toHaveFocus()
    await userEvent.tab({ shift: true })
    expect(confirmButton).toHaveFocus()
    await userEvent.tab()
    expect(cancelButton).toHaveFocus()
    fireEvent.keyDown(dialog, { key: 'Escape' })
    await waitFor(() => expect(clearTrigger).toHaveFocus())
    expect(screen.getByText('Question to clear')).toBeInTheDocument()

    await userEvent.click(clearTrigger)
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Clear conversation' }))
    expect(screen.queryByText('Question to clear')).not.toBeInTheDocument()
    expect(localStorage.getItem(publicChatStorageKey('GIT'))).toBeNull()
    expect(localStorage.getItem(publicChatStorageKey('OTHER'))).not.toBeNull()
    expect(input).toHaveFocus()
  })

  it('isolates institution histories on route changes and restores them on popstate navigation', async () => {
    writePublicChatHistory('GIT', [
      { id: 'git-u', role: 'user', content: 'GIT history', createdAt: 1 },
      { id: 'git-a', role: 'assistant', content: 'GIT answer', createdAt: 2 },
    ])
    writePublicChatHistory('COLLEGE-B', [
      { id: 'b-u', role: 'user', content: 'College B history', createdAt: 1 },
      { id: 'b-a', role: 'assistant', content: 'College B answer', createdAt: 2 },
    ])
    render(<App />)
    expect(screen.getByText('GIT history')).toBeInTheDocument()

    window.history.pushState({}, '', '/public-chat/COLLEGE-B')
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(await screen.findByText('College B history')).toBeInTheDocument()
    expect(screen.queryByText('GIT history')).not.toBeInTheDocument()

    window.history.replaceState({}, '', '/public-chat/GIT')
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(await screen.findByText('GIT history')).toBeInTheDocument()
    expect(screen.queryByText('College B history')).not.toBeInTheDocument()
  })

  it('aborts an interrupted request and never updates the unmounted page', async () => {
    let requestSignal: AbortSignal | undefined
    vi.mocked(publicChat).mockImplementationOnce((_request, options) => {
      requestSignal = typeof options === 'number' ? undefined : options?.signal
      return new Promise(() => undefined)
    })
    const view = render(<App />)
    const input = screen.getByLabelText('Ask a public college question')
    await userEvent.type(input, 'Long request{enter}')
    expect(screen.getByRole('status')).toHaveTextContent('Thinking')
    view.unmount()
    expect(requestSignal?.aborted).toBe(true)
  })

  it('restores an interrupted persisted turn as a retry without duplicating the user message', async () => {
    writePublicChatHistory('GIT', [
      { id: 'interrupted-u', role: 'user', content: 'Interrupted question', createdAt: 1 },
    ])
    vi.mocked(publicChat).mockResolvedValueOnce({
      answer: 'Recovered answer', status: 'success', sources: [],
    })
    render(<App />)
    expect(screen.getByRole('alert')).toHaveTextContent('previous request was interrupted')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Recovered answer')).toBeInTheDocument()
    expect(screen.getAllByText('Interrupted question')).toHaveLength(1)
    expect(publicChat).toHaveBeenCalledTimes(1)
  })

  it('hydrates malicious stored content as inert text', () => {
    writePublicChatHistory('GIT', [
      { id: 'xss-u', role: 'user', content: '<img src=x onerror=alert(1)>', createdAt: 1 },
      { id: 'xss-a', role: 'assistant', content: '<script>alert(1)</script>', createdAt: 2 },
    ])
    render(<App />)
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
    expect(document.querySelector('script')).toBeNull()
  })

  it('keeps the incomplete public route outside authentication', () => {
    window.history.replaceState({}, '', '/public-chat')
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Public chat link incomplete' })).toBeInTheDocument()
    expect(authProviderSpy).not.toHaveBeenCalled()
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../../App.tsx'
import { publicChat } from '../../services/publicChat.ts'

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

  it('keeps the incomplete public route outside authentication', () => {
    window.history.replaceState({}, '', '/public-chat')
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Public chat link incomplete' })).toBeInTheDocument()
    expect(authProviderSpy).not.toHaveBeenCalled()
  })
})

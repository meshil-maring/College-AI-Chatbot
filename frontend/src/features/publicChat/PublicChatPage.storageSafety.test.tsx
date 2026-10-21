import './__tests__/PublicChatPage.support.tsx'
import { authProviderSpy } from './__tests__/PublicChatPage.support.tsx'
import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../../App.tsx'
import { publicChat } from '../../services/chat/publicChat.ts'
import { writePublicChatHistory } from './publicChatStorage.ts'
describe('public chat route and conversation', () => {
  beforeEach(() => {
    localStorage.clear()
    authProviderSpy.mockClear()
    vi.mocked(publicChat).mockReset()
    window.history.replaceState({}, '', '/public-chat/GIT')
  })

  afterEach(() => window.history.replaceState({}, '', '/'))

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
    expect(screen.getByRole('link', { name: 'Go to platform gateway' })).toHaveAttribute('href', '/')
    expect(authProviderSpy).not.toHaveBeenCalled()
  })
})

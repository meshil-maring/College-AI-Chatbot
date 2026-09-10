/**
 * Phase Admin-4 — FaqManager CRUD tests.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FaqManager from './FaqManager.tsx'
import * as adminApi from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts')
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'test-token', user: null, logout: vi.fn() }),
}))

describe('FaqManager', () => {
  it('shows loading state initially', () => {
    vi.mocked(adminApi.listFaqs).mockReturnValue(new Promise(() => {}))
    render(<FaqManager />)
    expect(screen.getByText('Loading FAQs…')).toBeInTheDocument()
  })

  it('shows empty state when no FAQs', async () => {
    vi.mocked(adminApi.listFaqs).mockResolvedValue([])
    render(<FaqManager />)
    await waitFor(() => {
      expect(screen.getByText('No FAQs yet.')).toBeInTheDocument()
    })
  })

  it('lists FAQs after loading', async () => {
    vi.mocked(adminApi.listFaqs).mockResolvedValue([
      { faq_id: 'f1', question: 'What is the deadline?', answer: 'June 30.', is_active: true, category: 'general', display_order: 0, institution_id: null, created_at: '', updated_at: '' },
    ])
    render(<FaqManager />)
    await waitFor(() => {
      expect(screen.getByText('What is the deadline?')).toBeInTheDocument()
    })
  })

  it('opens form when Add FAQ is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listFaqs).mockResolvedValue([])
    render(<FaqManager />)
    await waitFor(() => { expect(screen.getByText('Add FAQ')).toBeInTheDocument() })
    await user.click(screen.getByText('Add FAQ'))
    expect(screen.getByText('New FAQ')).toBeInTheDocument()
  })

  it('creates a new FAQ', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listFaqs).mockResolvedValue([])
    vi.mocked(adminApi.createFaq).mockResolvedValue({
      faq_id: 'f2', question: 'New question?', answer: 'New answer.', is_active: true, category: 'general', display_order: 0, institution_id: null, created_at: '', updated_at: '',
    })
    render(<FaqManager />)
    await waitFor(() => { expect(screen.getByText('Add FAQ')).toBeInTheDocument() })
    await user.click(screen.getByText('Add FAQ'))
    await user.type(screen.getByLabelText('Question'), 'New question?')
    await user.type(screen.getByLabelText('Answer'), 'New answer.')
    await user.click(screen.getByText('Save'))
    await waitFor(() => {
      expect(adminApi.createFaq).toHaveBeenCalledWith('test-token', { question: 'New question?', answer: 'New answer.', category: 'general' })
    })
  })

  it('shows error when create fails', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listFaqs).mockResolvedValue([])
    vi.mocked(adminApi.createFaq).mockRejectedValue(new Error('Server error'))
    render(<FaqManager />)
    await waitFor(() => { expect(screen.getByText('Add FAQ')).toBeInTheDocument() })
    await user.click(screen.getByText('Add FAQ'))
    await user.type(screen.getByLabelText('Question'), 'Q')
    await user.type(screen.getByLabelText('Answer'), 'A')
    await user.click(screen.getByText('Save'))
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument()
    })
  })

  it('toggles FAQ active status', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.listFaqs).mockResolvedValue([
      { faq_id: 'f1', question: 'Q?', answer: 'A.', is_active: true, category: 'general', display_order: 0, institution_id: null, created_at: '', updated_at: '' },
    ])
    vi.mocked(adminApi.updateFaq).mockResolvedValue({
      faq_id: 'f1', question: 'Q?', answer: 'A.', is_active: false, category: 'general', display_order: 0, institution_id: null, created_at: '', updated_at: '',
    })
    render(<FaqManager />)
    await waitFor(() => { expect(screen.getByText('Unpublish')).toBeInTheDocument() })
    await user.click(screen.getByText('Unpublish'))
    await waitFor(() => {
      expect(adminApi.updateFaq).toHaveBeenCalledWith('test-token', 'f1', { is_active: false })
    })
  })
})

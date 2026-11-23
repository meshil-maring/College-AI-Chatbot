/**
 * FAQ feedback: success toasts appear only after the server confirms, and a
 * deletion runs only after the existing confirmation prompt is accepted.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FaqManager from './FaqManager.tsx'
import * as adminApi from '../../../services/admin/adminApi.ts'
import type { Faq } from '../../../types/admin.ts'

vi.mock('../../../services/admin/adminApi.ts')
vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'test-token', user: null, logout: vi.fn() }),
}))

const faq: Faq = {
  faq_id: 'f1',
  question: 'What is the deadline?',
  answer: 'June 30.',
  is_active: true,
  category: 'general',
  display_order: 0,
  institution_id: null,
  created_at: '',
  updated_at: '',
}

async function renderList() {
  vi.mocked(adminApi.listFaqs).mockResolvedValue([faq])
  render(<FaqManager />)
  await screen.findByText('What is the deadline?')
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('FaqManager notifications', () => {
  it('deletes only after confirmation and then shows one success toast', async () => {
    const user = userEvent.setup()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    let finish: () => void = () => {}
    vi.mocked(adminApi.deleteFaq).mockReturnValue(
      new Promise<void>((resolve) => {
        finish = resolve
      }) as never,
    )
    await renderList()
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(confirm).toHaveBeenCalledWith('Delete this FAQ?')
    expect(adminApi.deleteFaq).toHaveBeenCalledWith('test-token', 'f1')
    // The request is still in flight: no success yet.
    expect(screen.queryByText('FAQ deleted successfully')).not.toBeInTheDocument()
    finish()
    expect(await screen.findByText('FAQ deleted successfully')).toBeInTheDocument()
    expect(screen.getAllByText('FAQ deleted successfully')).toHaveLength(1)
    await waitFor(() => expect(screen.queryByText('What is the deadline?')).not.toBeInTheDocument())
  })

  it('does nothing when the confirmation is cancelled', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    await renderList()
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(adminApi.deleteFaq).not.toHaveBeenCalled()
    expect(screen.queryByText('FAQ deleted successfully')).not.toBeInTheDocument()
    expect(screen.getByText('What is the deadline?')).toBeInTheDocument()
  })

  it('reports a failed deletion inline and never as a success', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(adminApi.deleteFaq).mockRejectedValue(new Error('FAQ is in use.'))
    await renderList()
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('FAQ is in use.')
    expect(screen.queryByText('FAQ deleted successfully')).not.toBeInTheDocument()
    expect(screen.getByText('What is the deadline?')).toBeInTheDocument()
  })

  it('confirms publishing changes after the server responds', async () => {
    const user = userEvent.setup()
    vi.mocked(adminApi.updateFaq).mockResolvedValue({ ...faq, is_active: false })
    await renderList()
    await user.click(screen.getByRole('button', { name: 'Unpublish' }))
    expect(await screen.findByText('FAQ unpublished successfully')).toBeInTheDocument()
  })
})

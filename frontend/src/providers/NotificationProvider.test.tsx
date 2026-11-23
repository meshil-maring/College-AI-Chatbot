import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { notification } from '../lib/notifications/notification.ts'
import { NotificationProvider } from './NotificationProvider.tsx'

describe('NotificationProvider', () => {
  it('renders one labelled, dark, top-right toast region', async () => {
    render(<NotificationProvider />)
    expect(screen.getAllByRole('region', { name: /notifications/i })).toHaveLength(1)
    act(() => {
      notification.info('Welcome back')
    })
    await screen.findByText('Welcome back')
    const list = document.querySelector('[data-sonner-toaster]') as HTMLElement
    expect(list).toHaveAttribute('data-sonner-theme', 'dark')
    expect(list).toHaveAttribute('data-y-position', 'top')
    expect(list).toHaveAttribute('data-x-position', 'right')
  })

  it('lets keyboard users dismiss a toast with its labelled close button', async () => {
    const user = userEvent.setup()
    render(<NotificationProvider />)
    act(() => {
      notification.success('Changes saved successfully')
    })
    await screen.findByText('Changes saved successfully')
    const close = screen.getByRole('button', { name: 'Dismiss notification' })
    close.focus()
    await user.keyboard('{Enter}')
    await waitFor(() => expect(screen.queryByText('Changes saved successfully')).not.toBeInTheDocument())
  })
})

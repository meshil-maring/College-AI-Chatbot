import { act, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { AdminApiError } from '../../services/admin/http.ts'
import { NotificationProvider } from '../../providers/NotificationProvider.tsx'
import { notification } from './notification.ts'
import { GENERIC_FAILURE_DESCRIPTION } from './notificationErrors.ts'

function renderToaster() {
  render(<NotificationProvider />)
  return () => screen.getByRole('region', { name: /notifications/i })
}

function toasts() {
  return document.querySelectorAll('[data-sonner-toast]')
}

afterEach(() => {
  act(() => notification.dismiss())
})

describe('notification service', () => {
  it.each([
    ['success', 'Department created successfully'],
    ['error', 'Department could not be saved'],
    ['warning', 'Unsaved changes will be lost'],
    ['info', 'Semester registration opens on Monday'],
  ] as const)('shows a %s toast with its description', async (variant, message) => {
    renderToaster()
    act(() => {
      notification[variant](message, 'Supporting detail')
    })
    const toast = await screen.findByText(message)
    const item = toast.closest('[data-sonner-toast]') as HTMLElement
    expect(item).toHaveAttribute('data-type', variant)
    expect(within(item).getByText('Supporting detail')).toBeInTheDocument()
  })

  it('shows a loading toast until it is dismissed', async () => {
    renderToaster()
    let id: string | number = ''
    act(() => {
      id = notification.loading('Uploading document...')
    })
    const item = (await screen.findByText('Uploading document...')).closest('[data-sonner-toast]')
    expect(item).toHaveAttribute('data-type', 'loading')
    act(() => notification.dismiss(id))
    await waitFor(() => expect(screen.queryByText('Uploading document...')).not.toBeInTheDocument())
  })

  it('replaces a resolved promise toast with its success message', async () => {
    renderToaster()
    let finish: (value: string) => void = () => {}
    const pending = new Promise<string>((resolve) => {
      finish = resolve
    })
    let returned: Promise<string> | undefined
    act(() => {
      returned = notification.promise(pending, {
        loading: 'Uploading document...',
        success: (name) => `${name} uploaded successfully`,
        error: 'Document upload failed',
      })
    })
    expect(await screen.findByText('Uploading document...')).toBeInTheDocument()
    await act(async () => finish('Handbook'))
    expect(await screen.findByText('Handbook uploaded successfully')).toBeInTheDocument()
    expect(screen.queryByText('Uploading document...')).not.toBeInTheDocument()
    await expect(returned).resolves.toBe('Handbook')
  })

  it('replaces a rejected promise toast with a safe error and keeps the rejection', async () => {
    renderToaster()
    const failure = Promise.reject(new AdminApiError(500, 'relation "documents" does not exist'))
    let returned: Promise<unknown> | undefined
    act(() => {
      returned = notification.promise(failure, {
        loading: 'Uploading document...',
        success: 'Document uploaded successfully',
        error: 'Document upload failed',
      })
    })
    await expect(returned).rejects.toThrow('relation')
    expect(await screen.findByText('Document upload failed')).toBeInTheDocument()
    expect(screen.getByText(GENERIC_FAILURE_DESCRIPTION)).toBeInTheDocument()
    expect(screen.queryByText(/relation "documents"/)).not.toBeInTheDocument()
  })

  it('shows user-facing 4xx messages and skips expired sessions', async () => {
    renderToaster()
    act(() => {
      notification.requestFailed('Department could not be saved', new AdminApiError(409, 'Code already in use.'))
    })
    expect(await screen.findByText('Code already in use.')).toBeInTheDocument()
    let skipped: unknown
    act(() => {
      skipped = notification.requestFailed('Department could not be saved', new AdminApiError(401, 'expired'))
    })
    expect(skipped).toBeNull()
    expect(toasts()).toHaveLength(1)
  })

  it('does not stack the same message twice', async () => {
    renderToaster()
    act(() => {
      notification.success('Changes saved successfully')
      notification.success('Changes saved successfully')
    })
    await screen.findByText('Changes saved successfully')
    expect(screen.getAllByText('Changes saved successfully')).toHaveLength(1)
  })
})

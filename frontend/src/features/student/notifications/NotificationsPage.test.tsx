import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { queryClient } from '../../../lib/queryClient.ts'
import * as api from '../../../services/students/notificationsApi.ts'
import type { StudentNotification } from '../../../types/student.ts'
import NotificationsPage from './NotificationsPage.tsx'

const auth = vi.hoisted(() => ({
  accessToken: 'token-1',
  role: 'student',
  sessionGeneration: 1,
  user: {
    user_id: 'user-1',
    institution_id: 'tenant-1',
    effective_permissions: ['notifications.own.read', 'notifications.own.update'],
  },
}))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../services/students/notificationsApi.ts')

function notification(overrides: Partial<StudentNotification> = {}): StudentNotification {
  return {
    notification_id: 'n-1',
    student_id: 'student-1',
    institution_id: 'tenant-1',
    notification_type: 'academic_status',
    title: 'Transfer request approved',
    message: 'Your transfer was approved by the administrator.',
    is_read: false,
    source_type: 'student_transfer',
    source_record_id: 'request-1',
    created_at: '2026-11-21T10:00:00Z',
    read_at: null,
    ...overrides,
  }
}

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  vi.mocked(api.getMyNotifications).mockResolvedValue({
    items: [
      notification(),
      notification({
        notification_id: 'n-2',
        title: 'Results published',
        source_type: 'academic_event',
        is_read: true,
      }),
    ],
    total: 2,
    page: 1,
    page_size: 50,
    has_more: false,
  })
  vi.mocked(api.markNotificationRead).mockResolvedValue(notification({ is_read: true }))
})
afterEach(() => queryClient.clear())

it('shows transfer decisions, filters unread and opens Transfer Requests', async () => {
  const onOpenTransfers = vi.fn()
  render(<NotificationsPage onOpenTransfers={onOpenTransfers} />)
  expect(await screen.findByText('Transfer request approved')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Unread (1)' }))
  expect(screen.queryByText('Results published')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Open Transfer Requests' }))
  expect(onOpenTransfers).toHaveBeenCalledOnce()
})

it('marks one or all unread notifications as read', async () => {
  render(<NotificationsPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'Mark as read' }))
  await waitFor(() => expect(api.markNotificationRead).toHaveBeenCalledExactlyOnceWith('token-1', 'n-1'))
  fireEvent.click(screen.getByRole('button', { name: 'Mark all as read' }))
  await waitFor(() => expect(api.markNotificationRead).toHaveBeenCalledTimes(2))
})

it('refuses notifications from another institution', async () => {
  vi.mocked(api.getMyNotifications).mockResolvedValue({
    items: [notification({ institution_id: 'tenant-2' })],
    total: 1,
    page: 1,
    page_size: 50,
    has_more: false,
  })
  render(<NotificationsPage />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Notifications are unavailable for this institution.')
})

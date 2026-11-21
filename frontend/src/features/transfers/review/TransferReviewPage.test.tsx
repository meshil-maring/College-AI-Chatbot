import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { queryClient } from '../../../lib/queryClient.ts'
import * as api from '../../../services/students/transferApi.ts'
import TransferReviewPage from './TransferReviewPage.tsx'
import { requestFixture, reviewsFixture, sectionFixture } from '../__tests__/transferFixture.ts'

const auth = vi.hoisted(() => ({
  accessToken: 'token-1',
  role: 'faculty',
  sessionGeneration: 1,
  user: { user_id: 'user-1', institution_id: 'tenant-1', effective_permissions: [] as string[] },
}))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../services/students/transferApi.ts')

const decided = (status: 'approved' | 'rejected' | 'under_review') => ({
  transfer_request_id: 'request-1',
  institution_id: 'tenant-1',
  status,
})

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  vi.mocked(api.getTransferReviews).mockResolvedValue(reviewsFixture())
})
afterEach(() => queryClient.clear())

it('tells a faculty member without an HOD appointment that nothing is assigned', async () => {
  vi.mocked(api.getTransferReviews).mockResolvedValue(
    reviewsFixture({ can_review: false, can_decide: false, reviewer_role: null, departments: [], requests: [] }),
  )
  render(<TransferReviewPage />)
  expect(await screen.findByText(/not an administrator or a current Head of Department/)).toBeInTheDocument()
})

it('lets an HOD approve with an optional note after confirmation', async () => {
  vi.mocked(api.decideTransfer).mockResolvedValue(decided('approved'))
  render(<TransferReviewPage />)
  expect(await screen.findByText(/transfers into Computer Science as Head of Department/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
  expect(screen.getByText(/must register again/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Confirm approval' }))
  await waitFor(() =>
    expect(api.decideTransfer).toHaveBeenCalledExactlyOnceWith('token-1', 'request-1', 'approve', null),
  )
  expect(await screen.findByText(/Asha Rao was moved to the new section/)).toBeInTheDocument()
})

it('requires a reason before rejecting', async () => {
  vi.mocked(api.decideTransfer).mockResolvedValue(decided('rejected'))
  render(<TransferReviewPage />)
  fireEvent.click(await screen.findByRole('button', { name: 'Reject' }))
  const confirm = screen.getByRole('button', { name: 'Confirm rejection' })
  expect(confirm).toBeDisabled()
  fireEvent.change(screen.getByLabelText(/Reason for rejection/), { target: { value: ' Section is full ' } })
  fireEvent.click(confirm)
  await waitFor(() =>
    expect(api.decideTransfer).toHaveBeenCalledExactlyOnceWith('token-1', 'request-1', 'reject', 'Section is full'),
  )
})

it('blocks approval into a full section from a single load of every request', async () => {
  vi.mocked(api.getTransferReviews).mockResolvedValue(
    reviewsFixture({
      reviewer_role: 'admin',
      requests: [requestFixture({ to_section: sectionFixture({ section_name: 'B', capacity: 40, seats_taken: 40 }) })],
    }),
  )
  render(<TransferReviewPage />)
  expect(await screen.findByText(/full — approval will fail/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
  expect(api.getTransferReviews).toHaveBeenCalledExactlyOnceWith('token-1', 'all', expect.anything())
})

it('searches, filters and shows decided transfers under History', async () => {
  vi.mocked(api.getTransferReviews).mockResolvedValue(
    reviewsFixture({
      reviewer_role: 'admin',
      requests: [
        requestFixture(),
        requestFixture({
          transfer_request_id: 'request-2',
          student_name: 'Ravi Kumar',
          register_number: 'REG-002',
          status: 'approved',
          initiated_by: 'admin',
          decided_at: '2026-11-20T12:00:00Z',
          decided_as: 'admin',
        }),
        requestFixture({
          transfer_request_id: 'request-3',
          student_name: 'Meera Das',
          status: 'rejected',
          decided_at: '2026-11-20T13:00:00Z',
          decided_as: 'hod',
          decision_comment: 'Section full',
        }),
      ],
    }),
  )
  render(<TransferReviewPage />)
  const pending = await screen.findByRole('list', { name: 'Pending transfer requests' })
  expect(pending.querySelectorAll(':scope > li')).toHaveLength(1)
  fireEvent.click(screen.getByRole('tab', { name: /History \(2\)/ }))
  const history = screen.getByRole('list', { name: 'Transfer history' })
  expect(history).toHaveTextContent('Ravi Kumar')
  expect(history).toHaveTextContent('Meera Das')
  fireEvent.change(screen.getByLabelText('Started by'), { target: { value: 'admin' } })
  expect(screen.getByRole('list', { name: 'Transfer history' })).not.toHaveTextContent('Meera Das')
  fireEvent.change(screen.getByLabelText('Started by'), { target: { value: 'all' } })
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'reg-002' } })
  expect(screen.getByRole('list', { name: 'Transfer history' })).toHaveTextContent('Ravi Kumar')
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'nobody' } })
  expect(screen.getByText('No transfer requests match these filters.')).toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' })[0])
  fireEvent.click(screen.getByRole('button', { name: /Rejected/ }))
  expect(screen.getByRole('list', { name: 'Transfer history' })).not.toHaveTextContent('Ravi Kumar')
  fireEvent.click(screen.getAllByRole('button', { name: /Show details and history/ })[0])
  expect(screen.getByText('Section full')).toBeInTheDocument()
})

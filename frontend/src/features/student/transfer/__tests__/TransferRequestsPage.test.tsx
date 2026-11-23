import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { queryClient } from '../../../../lib/queryClient.ts'
import * as api from '../../../../services/students/transferApi.ts'
import TransferRequestsPage from '../TransferRequestsPage.tsx'
import { requestFixture, studentTransfersFixture } from '../../../transfers/__tests__/transferFixture.ts'

const auth = vi.hoisted(() => ({
  accessToken: 'token-1',
  role: 'student',
  sessionGeneration: 1,
  user: {
    user_id: 'user-1',
    institution_id: 'tenant-1',
    effective_permissions: ['transfers.read', 'transfers.request'],
  },
}))
vi.mock('../../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../../services/students/transferApi.ts')

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  auth.user.effective_permissions = ['transfers.read', 'transfers.request']
  vi.mocked(api.getMyTransfers).mockResolvedValue(studentTransfersFixture())
})
afterEach(() => queryClient.clear())

it('submits only the chosen section and a trimmed reason', async () => {
  vi.mocked(api.submitTransfer).mockResolvedValue({
    transfer_request_id: 'request-1',
    institution_id: 'tenant-1',
    status: 'submitted',
  })
  render(<TransferRequestsPage />)
  expect(await screen.findByText(/B.Tech CSE · Section A/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Request a transfer' }))
  const submit = screen.getByRole('button', { name: 'Submit request' })
  expect(screen.getByRole('radio', { name: /B.Tech ECE/ })).toBeDisabled()
  fireEvent.click(screen.getByRole('radio', { name: /Section B/ }))
  fireEvent.change(screen.getByLabelText('Reason for the transfer'), { target: { value: '  Clash with lab hours  ' } })
  expect(submit).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox', { name: /register my subjects again/ }))
  fireEvent.click(submit)
  await waitFor(() =>
    expect(api.submitTransfer).toHaveBeenCalledExactlyOnceWith('token-1', {
      to_section_id: 'section-b',
      reason: 'Clash with lab hours',
    }),
  )
  expect(await screen.findByText('Transfer request submitted successfully')).toBeInTheDocument()
})

it('offers cancel instead of a new request while one is open', async () => {
  vi.mocked(api.getMyTransfers).mockResolvedValue(studentTransfersFixture({ requests: [requestFixture()] }))
  vi.mocked(api.cancelTransfer).mockResolvedValue({
    transfer_request_id: 'request-1',
    institution_id: 'tenant-1',
    status: 'cancelled',
  })
  render(<TransferRequestsPage />)
  expect(await screen.findByText(/You have an open request/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Request a transfer' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Cancel request' }))
  expect(api.cancelTransfer).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Yes, cancel it' }))
  await waitFor(() => expect(api.cancelTransfer).toHaveBeenCalledExactlyOnceWith('token-1', 'request-1'))
})

it('shows the rejection reason and hides requests without the request permission', async () => {
  auth.user.effective_permissions = ['transfers.read']
  vi.mocked(api.getMyTransfers).mockResolvedValue(
    studentTransfersFixture({
      requests: [requestFixture({ status: 'rejected', decided_as: 'hod', decision_comment: 'Section B is full.' })],
    }),
  )
  render(<TransferRequestsPage />)
  expect(await screen.findByText('Section B is full.')).toBeInTheDocument()
  expect(screen.getByText(/Rejection reason \(HOD\)/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Request a transfer' })).not.toBeInTheDocument()
})

it('rejects data from another institution', async () => {
  vi.mocked(api.getMyTransfers).mockResolvedValue(studentTransfersFixture({ institution_id: 'tenant-2' }))
  render(<TransferRequestsPage />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Transfer data is unavailable for this institution.')
})

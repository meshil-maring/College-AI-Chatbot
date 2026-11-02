import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentManager from '../StudentManager.tsx'
import type { StudentDirectoryResponse } from '../../../../types/admin/students.ts'

const auth = vi.hoisted(() => ({
  user: { user_id: 'user-1', institution_id: 'institution-1' },
  accessToken: 'token',
}))
const permission = vi.hoisted(() => ({ canAll: vi.fn(() => true) }))
const api = vi.hoisted(() => ({ getStudentDirectory: vi.fn(), resendStudentInvitation: vi.fn() }))
vi.mock('../../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => auth }))
vi.mock('../../../auth/access/usePermissions.ts', () => ({ usePermissions: () => permission }))
vi.mock('../AdminApprovals.tsx', () => ({ default: () => null }))
vi.mock('../../student-onboarding/StudentOnboardingPage.tsx', () => ({ default: () => null }))
vi.mock('../../../../services/admin/students.ts', () => api)

const directory: StudentDirectoryResponse = {
  items: [],
  total: 0,
  limit: 25,
  offset: 0,
  summary: { total: 0, pending_sign_in: 0, signed_in: 0, no_signin: 0 },
  programs: [],
}

function renderManager() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <StudentManager page="all" />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  permission.canAll.mockReturnValue(true)
  api.getStudentDirectory.mockResolvedValue(directory)
})

describe('StudentManager All Students access', () => {
  it('shows the directory to a user with students.read', async () => {
    renderManager()

    expect(await screen.findByText('No student accounts or setup invitations have been added yet.')).toBeInTheDocument()
    expect(permission.canAll).toHaveBeenCalledWith('students.read')
  })

  it('does not request directory data without students.read', () => {
    permission.canAll.mockReturnValue(false)
    renderManager()

    expect(screen.getByRole('status')).toHaveTextContent('does not have permission to view students')
    expect(api.getStudentDirectory).not.toHaveBeenCalled()
  })
})

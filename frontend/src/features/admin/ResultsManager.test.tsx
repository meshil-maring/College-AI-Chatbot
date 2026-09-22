/**
 * Phase 6.19 — ResultsManager CSV upload contract tests.
 *
 * The CSV upload goes to the verified backend contract
 * POST /admin/results/csv-upload with the required `institution_id` field
 * taken from the AuthProvider tenant, and the message reflects the backend
 * `CsvUploadResult` shape ({total_rows, inserted_count, failed_count}).
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ResultsManager from './ResultsManager.tsx'
import type { StudentResult } from '../../types/admin.ts'

const adminApi = vi.hoisted(() => ({
  listStudentResults: vi.fn(),
  uploadResultsCsv: vi.fn(),
}))

vi.mock('../../services/adminApi.ts', () => adminApi)

/** Mutable auth context so each test can drive the linked tenant. */
const authState = vi.hoisted(() => ({
  accessToken: 'test-token' as string | null,
  user: {
    authenticated: true,
    user_id: 'u1',
    auth_user_id: 'a1',
    email: 'admin@test.com',
    role: 'admin' as const,
    institution_id: 'inst-1',
  },
}))

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

beforeEach(() => {
  authState.accessToken = 'test-token'
  authState.user.institution_id = 'inst-1'
  adminApi.listStudentResults.mockReset().mockResolvedValue([] as StudentResult[])
  adminApi.uploadResultsCsv.mockReset()
})

describe('ResultsManager CSV upload', () => {
  it('sends the tenant from auth state and reports the backend result shape', async () => {
    const user = userEvent.setup()
    adminApi.uploadResultsCsv.mockResolvedValue({
      total_rows: 3,
      inserted_count: 2,
      failed_count: 1,
      row_errors: [{ row: 3, student_number: 'S999', errors: ['not found'] }],
    })
    render(<ResultsManager />)
    const input = screen.getByLabelText('Upload Results CSV')
    await user.upload(input, new File(['student_number'], 'results.csv', { type: 'text/csv' }))
    await waitFor(() => {
      expect(adminApi.uploadResultsCsv).toHaveBeenCalledWith(
        'test-token',
        expect.any(File),
        'inst-1',
      )
    })
    await waitFor(() => {
      expect(screen.getByText(/Uploaded 2 of 3 rows; 1 row\(s\) failed/)).toBeInTheDocument()
    })
  })

  it('reports a fully successful upload', async () => {
    const user = userEvent.setup()
    adminApi.uploadResultsCsv.mockResolvedValue({
      total_rows: 2,
      inserted_count: 2,
      failed_count: 0,
      row_errors: [],
    })
    render(<ResultsManager />)
    await user.upload(
      screen.getByLabelText('Upload Results CSV'),
      new File(['student_number'], 'results.csv', { type: 'text/csv' }),
    )
    await waitFor(() => {
      expect(screen.getByText(/Successfully uploaded 2 of 2 rows/)).toBeInTheDocument()
    })
  })

  it('disables upload and shows a neutral status when no institution is linked', () => {
    authState.user.institution_id = null
    render(<ResultsManager />)
    const input = screen.getByLabelText('Upload Results CSV') as HTMLInputElement
    expect(input.disabled).toBe(true)
    expect(screen.getByText(/No institution is linked/)).toBeInTheDocument()
  })
})
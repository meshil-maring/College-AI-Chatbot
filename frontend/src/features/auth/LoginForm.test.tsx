/**
 * DEVELOPMENT / TESTING ONLY (partial) — tests for the "Forgot Password?"
 * link visibility gate in LoginForm, driven by the backend dev/test flag.
 */

/// <reference types="vitest/globals" />
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import LoginForm from './LoginForm.tsx'
import * as devAuth from '../../services/devAuth.ts'

vi.mock('../../services/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../services/devAuth.ts')>(
    '../../services/devAuth.ts',
  )
  return { ...actual, fetchDevAuthStatus: vi.fn() }
})

vi.mock('./AuthProvider.tsx', () => ({
  useAuth: () => ({
    status: 'unauthenticated',
    user: null,
    accessToken: null,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

describe('LoginForm — dev/test "Forgot Password?" gating', () => {
  it('hides the Forgot Password link when dev/test mode is disabled', async () => {
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: false })
    render(<LoginForm />)

    await waitFor(() => {
      expect(devAuth.fetchDevAuthStatus).toHaveBeenCalled()
    })
    expect(screen.queryByText(/forgot password/i)).not.toBeInTheDocument()
  })

  it('shows the Forgot Password link when dev/test mode is enabled', async () => {
    vi.mocked(devAuth.fetchDevAuthStatus).mockResolvedValue({ dev_test_mode: true })
    render(<LoginForm />)

    expect(await screen.findByText(/forgot password/i)).toBeInTheDocument()
  })
})

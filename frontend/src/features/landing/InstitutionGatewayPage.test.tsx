import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../../App.tsx'
import { lookupInstitution, RegistrationError } from '../../services/registration/registration.ts'

vi.mock('../../services/registration/registration.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../services/registration/registration.ts')>()
  return { ...actual, lookupInstitution: vi.fn() }
})

vi.mock('../auth/session/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => { throw new Error('Public institution routes must not use authentication') },
}))

describe('institution presentation gateway', () => {
  beforeEach(() => {
    vi.mocked(lookupInstitution).mockReset()
    window.history.replaceState({}, '', '/u')
  })

  afterEach(() => window.history.replaceState({}, '', '/'))

  it('verifies a selected institution and opens its code-based gateway', async () => {
    vi.mocked(lookupInstitution).mockResolvedValue({
      institution_id: 'institution-1',
      code: 'GIT',
      name: 'Greenfield Institute of Technology',
    })
    render(<App />)
    await userEvent.type(screen.getByLabelText('Institution code'), 'git')
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(await screen.findByRole('heading', { name: 'Greenfield Institute of Technology' })).toBeInTheDocument()
    expect(lookupInstitution).toHaveBeenCalledWith('GIT')
    expect(screen.getByRole('link', { name: /Open public AI/ })).toHaveAttribute('href', '/u/git/ai')
    expect(screen.getByRole('link', { name: /Continue securely/ })).toHaveAttribute('href', '/login/student?institution=GIT')
    expect(screen.getByRole('link', { name: 'Register as Student' })).toHaveAttribute('href', '/login/student?institution=GIT&register=1')
  })

  it('shows a safe error instead of backend diagnostics', async () => {
    vi.mocked(lookupInstitution).mockRejectedValue(new Error('database host and secret details'))
    render(<App />)
    await userEvent.type(screen.getByLabelText('Institution code'), 'GIT')
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not find that institution right now')
    expect(document.body).not.toHaveTextContent('database host and secret details')
  })

  it('lets a direct gateway visit recover after a temporary lookup outage', async () => {
    window.history.replaceState({}, '', '/u/git')
    vi.mocked(lookupInstitution)
      .mockRejectedValueOnce(new RegistrationError('unavailable', 503, 'INSTITUTION_LOOKUP_UNAVAILABLE'))
      .mockResolvedValueOnce({ institution_id: 'institution-1', code: 'GIT', name: 'Greenfield Institute of Technology' })
    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Institution verification is temporarily unavailable')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'Greenfield Institute of Technology' })).toBeInTheDocument()
    expect(lookupInstitution).toHaveBeenCalledTimes(2)
  })
})


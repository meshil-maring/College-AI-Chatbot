import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UniversityRegistrationPage from './UniversityRegistrationPage.tsx'
import { registerUniversity } from '../../services/universityRegistration.ts'

vi.mock('../../services/universityRegistration.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../services/universityRegistration.ts')>()
  return { ...actual, registerUniversity: vi.fn() }
})

describe('UniversityRegistrationPage', () => {
  beforeEach(() => vi.mocked(registerUniversity).mockReset())

  it('registers an active university admin without a Platform Manager approval step', async () => {
    vi.mocked(registerUniversity).mockResolvedValue({
      message: 'University registered and activated. The University Admin can sign in now.',
      institution_code: 'ABCU',
      status: 'active',
      email: 'admin@abcu.edu',
    })
    const user = userEvent.setup()
    render(<UniversityRegistrationPage />)

    await user.type(screen.getByLabelText('University name'), 'ABC University')
    await user.type(screen.getByLabelText('University code'), 'abcu')
    await user.type(screen.getByLabelText('Official university email'), 'office@abcu.edu')
    await user.type(screen.getByLabelText('First name'), 'Ada')
    await user.type(screen.getByLabelText('Last name'), 'Admin')
    await user.type(screen.getByLabelText('Admin email'), 'admin@abcu.edu')
    await user.type(screen.getByLabelText('Password'), 'strongpass')
    await user.type(screen.getByLabelText('Confirm password'), 'strongpass')
    await user.click(screen.getByRole('button', { name: 'Register university' }))

    expect(registerUniversity).toHaveBeenCalledWith(expect.objectContaining({
      name: 'ABC University',
      institution_code: 'ABCU',
      organization_code: 'COLLEGE-AI-PLATFORM',
      admin_email: 'admin@abcu.edu',
      admin_password: 'strongpass',
    }))
    expect(await screen.findByRole('heading', { name: 'Your university is ready' })).toBeInTheDocument()
    expect(screen.getByText('Your University Admin account is active. You can sign in now.')).toBeInTheDocument()
  })

  it('does not submit when password confirmation differs', async () => {
    const user = userEvent.setup()
    render(<UniversityRegistrationPage />)
    await user.type(screen.getByLabelText('University name'), 'ABC University')
    await user.type(screen.getByLabelText('University code'), 'ABCU')
    await user.type(screen.getByLabelText('Official university email'), 'office@abcu.edu')
    await user.type(screen.getByLabelText('First name'), 'Ada')
    await user.type(screen.getByLabelText('Last name'), 'Admin')
    await user.type(screen.getByLabelText('Admin email'), 'admin@abcu.edu')
    await user.type(screen.getByLabelText('Password'), 'strongpass')
    await user.type(screen.getByLabelText('Confirm password'), 'different')
    await user.click(screen.getByRole('button', { name: 'Register university' }))

    expect(screen.getByRole('alert')).toHaveTextContent('The two passwords do not match.')
    expect(registerUniversity).not.toHaveBeenCalled()
  })
})

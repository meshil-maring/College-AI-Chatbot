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

  it('submits the backend institution-registration contract and shows pending state', async () => {
    vi.mocked(registerUniversity).mockResolvedValue({
      message: 'University registration submitted for approval.',
      institution_code: 'ABCU',
      status: 'pending',
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
    await user.click(screen.getByRole('button', { name: 'Submit university registration' }))

    expect(registerUniversity).toHaveBeenCalledWith(expect.objectContaining({
      name: 'ABC University',
      institution_code: 'ABCU',
      organization_code: 'COLLEGE-AI-PLATFORM',
      admin_email: 'admin@abcu.edu',
      admin_password: 'strongpass',
    }))
    expect(await screen.findByRole('heading', { name: 'Your university is pending approval' })).toBeInTheDocument()
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
    await user.click(screen.getByRole('button', { name: 'Submit university registration' }))

    expect(screen.getByRole('alert')).toHaveTextContent('The two passwords do not match.')
    expect(registerUniversity).not.toHaveBeenCalled()
  })
})

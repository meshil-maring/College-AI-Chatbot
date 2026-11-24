import { chooseSection, mocks, renderPage } from '../__tests__/onboarding.support.tsx'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

type User = ReturnType<typeof userEvent.setup>

async function openDetails(user: User) {
  await chooseSection(user)
  await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
}

async function fillAndReview(user: User, email = 'ada@example.com') {
  await user.type(screen.getByRole('textbox', { name: /Student name/ }), 'Ada Lovelace')
  await user.type(screen.getByRole('textbox', { name: /Register number/ }), 'REG-1')
  await user.type(screen.getByRole('textbox', { name: /Email address/ }), email)
  await user.click(screen.getByRole('button', { name: 'Review details' }))
}

describe('single student registration workflow', () => {
  it('picks a batch first and selects its only section automatically', async () => {
    const user = userEvent.setup()
    renderPage()
    expect(screen.queryByRole('group', { name: /Section/ })).not.toBeInTheDocument()
    await chooseSection(user)
    expect(screen.getByRole('radio', { name: /Section A/ })).toBeChecked()
    expect(screen.getByText('The student will be added to').parentElement).toHaveTextContent('Section A')
  })

  it('explains missing or invalid details on submit and focuses the first problem', async () => {
    const user = userEvent.setup()
    renderPage()
    await openDetails(user)
    expect(screen.getByText(/Placing in/)).toHaveTextContent('CSE8777912026 / A · Section A')

    await user.type(screen.getByRole('textbox', { name: /Email address/ }), 'not-an-email')
    await user.click(screen.getByRole('button', { name: 'Review details' }))

    const name = screen.getByRole('textbox', { name: /Student name/ })
    expect(name).toHaveFocus()
    expect(name).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Enter the register number.')).toBeInTheDocument()
    expect(screen.getByText(/Enter a valid email address/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Enter the student’s details' })).toBeInTheDocument()
  })

  it('warns about existing students on the review step before anything is created', async () => {
    const user = userEvent.setup()
    mocks.reviewIdentity.mockResolvedValue({
      students: [
        {
          student_name: 'Ada Lovelace',
          email: 'ada@example.com',
          register_number: 'REG-1',
          university_roll_number: null,
          approval_status: 'approved',
          account_status: 'active',
          student_status: 'active',
          is_active: true,
          has_signed_in: true,
          last_sign_in_at: null,
        },
      ],
      invitations: [],
      email_conflict_exists: true,
    })
    renderPage()
    await openDetails(user)
    await fillAndReview(user)

    const warning = await screen.findByText('This student may already be registered')
    expect(warning.parentElement).toHaveTextContent('Register REG-1')
    expect(mocks.createSingle).not.toHaveBeenCalled()
    await user.click(within(warning.parentElement as HTMLElement).getByRole('button', { name: 'Edit details' }))
    expect(screen.getByRole('textbox', { name: /Student name/ })).toHaveValue('Ada Lovelace')
  })

  it('returns to a completed step from the progress indicator', async () => {
    const user = userEvent.setup()
    renderPage()
    await openDetails(user)
    await fillAndReview(user)
    await user.click(screen.getByRole('button', { name: /Placement.*go back/ }))
    expect(screen.getByRole('heading', { name: 'Where should this student be enrolled?' })).toBeInTheDocument()
  })

  it('keeps the placement for the next student and links to All Students', async () => {
    const user = userEvent.setup()
    renderPage()
    await openDetails(user)
    await fillAndReview(user)
    await user.click(screen.getByRole('button', { name: /Create account & send link/ }))

    const result = await screen.findByRole('region', { name: 'Registration result' })
    expect(within(result).getByRole('link', { name: 'View in All Students' })).toHaveAttribute(
      'href',
      expect.stringContaining('student-page=all'),
    )
    expect(result).toHaveTextContent('Next student goes to CSE8777912026 / A · Section A')
    await user.click(within(result).getByRole('button', { name: /Register another student/ }))
    expect(screen.getByRole('textbox', { name: /Student name/ })).toHaveValue('')
    expect(screen.getByText(/Placing in/)).toHaveTextContent('Section A')
  })

  it('resends a failed setup email from the result card', async () => {
    const user = userEvent.setup()
    mocks.createSingle.mockResolvedValue({
      invitation: { invitation_id: 'invite-9', email: 'ada@example.com' },
      delivery_status: 'failed',
      delivery_message: 'Email failed.',
    })
    mocks.resend.mockResolvedValue({ delivery_status: 'sent', delivery_message: 'Setup link sent.' })
    renderPage()
    await openDetails(user)
    await fillAndReview(user)
    await user.click(screen.getByRole('button', { name: /Create account & send link/ }))

    await user.click(await screen.findByRole('button', { name: /Resend setup link/ }))
    expect(mocks.resend).toHaveBeenCalledWith('token', 'invite-9')
    await waitFor(() => expect(screen.getByText('Student registration is underway')).toBeInTheDocument())
  })
})

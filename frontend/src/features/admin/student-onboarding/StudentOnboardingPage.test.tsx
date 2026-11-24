import { chooseSection, invitation, mocks, queryData, renderPage } from './__tests__/onboarding.support.tsx'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

async function fillDetails(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole('textbox', { name: /Student name/ }), 'Ada Lovelace')
  await user.type(screen.getByRole('textbox', { name: /Register number/ }), 'REG-1')
  await user.type(screen.getByRole('textbox', { name: /Email address/ }), 'ada@example.com')
}

describe('Add Student page', () => {
  it('shows one title, the wizard, invitation metrics and a link to bulk import', () => {
    queryData.invitations = [invitation(), invitation({ invitation_id: 'invite-2', email_delivery_status: 'failed' })]
    renderPage()

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    expect(screen.getByRole('heading', { level: 1, name: 'Add Student' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent('Students›Add Student')
    expect(screen.getByRole('link', { name: /Import from spreadsheet/ })).toHaveAttribute(
      'href',
      expect.stringContaining('student-page=bulk'),
    )
    expect(screen.queryByRole('group', { name: 'Choose registration method' })).not.toBeInTheDocument()
    expect(screen.getByText('Awaiting account setup').parentElement).toHaveTextContent('2')
    expect(screen.getByText('Email delivery issues').parentElement).toHaveTextContent('1')
    expect(screen.getByRole('table')).toHaveTextContent('Ada Lovelace')
  })

  it('links reviewers to waiting self-registration requests instead of embedding the queue', () => {
    queryData.pendingStudents = [{ student_id: 's-1' }, { student_id: 's-2' }]
    renderPage({ canReview: true })
    const notice = screen.getByRole('complementary', { name: 'Registration requests' })
    expect(notice).toHaveTextContent('2 self-registration requests are waiting for review.')
    expect(within(notice).getByRole('link', { name: /Review requests/ })).toHaveAttribute(
      'href',
      expect.stringContaining('student-page=requests'),
    )
  })

  it('hides the requests notice when nothing is waiting or the admin cannot review', () => {
    renderPage({ canReview: true })
    expect(screen.queryByRole('complementary', { name: 'Registration requests' })).not.toBeInTheDocument()
  })

  it('guides single registration through placement, details, review, and confirmation', async () => {
    const user = userEvent.setup()
    renderPage()
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
    expect(screen.getByRole('heading', { name: 'Enter the student’s details' })).toBeInTheDocument()

    await fillDetails(user)
    await user.click(screen.getByRole('button', { name: 'Review details' }))

    expect(screen.getByText('Academic placement').parentElement).toHaveTextContent('CSE8777912026')
    expect(screen.getByText('Academic placement').parentElement).toHaveTextContent('Section A')
    await user.click(screen.getByRole('button', { name: /Create account & send link/ }))
    expect(await screen.findByText('Student registration is underway')).toBeInTheDocument()
    expect(mocks.createSingle).toHaveBeenCalledWith(
      'token',
      'section-1',
      expect.objectContaining({ student_name: 'Ada Lovelace', register_number: 'REG-1' }),
    )
  })

  it('returns from student details to placement without losing typed details', async () => {
    const user = userEvent.setup()
    renderPage()
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
    await fillDetails(user)
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByLabelText(/Batch and section/)).toHaveValue('section-1')
    await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
    expect(screen.getByRole('textbox', { name: /Student name/ })).toHaveValue('Ada Lovelace')
  })

  it('submits registration directly and shows server-side duplicate conflicts', async () => {
    const user = userEvent.setup()
    window.history.replaceState(null, '', '/login/admin')
    mocks.createSingle.mockRejectedValueOnce(
      new Error('Email, Register Number, or University Roll No. is already in use'),
    )
    renderPage()
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
    await fillDetails(user)
    await user.click(screen.getByRole('button', { name: 'Review details' }))
    await user.click(screen.getByRole('button', { name: /Create account & send link/ }))
    const conflict = await screen.findByRole('alert')
    expect(conflict).toHaveTextContent('Email, Register Number, or University Roll No. is already in use')
    expect(within(conflict).getByRole('link', { name: 'Open All Students' })).toHaveAttribute(
      'href',
      '/login/admin?view=approvals&student-page=all',
    )
    expect(await within(conflict).findByText(/No matching student or pending invitation was found/)).toBeInTheDocument()
    expect(conflict).toHaveTextContent('that account has no student record here')
    expect(mocks.reviewIdentity).toHaveBeenCalledWith('token', {
      email: 'ada@example.com',
      register_number: 'REG-1',
      university_roll_number: null,
    })
    expect(mocks.createSingle).toHaveBeenCalledOnce()
  })
})

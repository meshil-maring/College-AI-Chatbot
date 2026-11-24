import { invitation, mocks, queryData, renderPage, structure } from '../__tests__/onboarding.support.tsx'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

const secondSection = {
  academic_section_id: 'section-2',
  admission_cohort_id: 'batch-1',
  code: 'B',
  name: 'Section B',
  is_active: true,
}

function table() {
  return screen.getByRole('table', { name: 'Pending student setup invitations' })
}

describe('pending invitations', () => {
  beforeEach(() => {
    structure.records.academic_sections.push(secondSection)
    queryData.invitations = [
      invitation(),
      invitation({
        invitation_id: 'invite-2',
        student_name: 'Grace Hopper',
        email: 'grace@example.com',
        register_number: 'REG-2',
        email_delivery_status: 'failed',
      }),
      invitation({
        invitation_id: 'invite-3',
        student_name: 'Alan Turing',
        email: 'alan@example.com',
        register_number: 'REG-3',
        expires_at: '2020-01-01T00:00:00Z',
      }),
    ]
  })
  afterEach(() => {
    structure.records.academic_sections.splice(1)
  })

  it('searches by name, email or register number', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByRole('searchbox', { name: 'Search pending invitations' }), 'reg-2')
    expect(within(table()).getAllByRole('row')).toHaveLength(2)
    expect(table()).toHaveTextContent('Grace Hopper')
    expect(screen.getByText('1 of 3 shown')).toBeInTheDocument()
  })

  it('filters by status from the summary cards and marks expired links', async () => {
    const user = userEvent.setup()
    renderPage()
    const expired = screen.getByRole('button', { name: /Expired setup links/ })
    expect(expired).toHaveTextContent('1')
    await user.click(expired)
    expect(expired).toHaveAttribute('aria-pressed', 'true')
    expect(within(table()).getAllByRole('row')).toHaveLength(2)
    expect(table()).toHaveTextContent('Link expired')
    expect(within(table()).getByRole('button', { name: 'Send new link to Alan Turing' })).toBeInTheDocument()

    await user.click(expired)
    expect(within(table()).getAllByRole('row')).toHaveLength(4)
  })

  it('offers a way out when nothing matches', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(screen.getByRole('searchbox', { name: 'Search pending invitations' }), 'nobody')
    expect(screen.getByText(/No invitations match/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear search and filter' }))
    expect(within(table()).getAllByRole('row')).toHaveLength(4)
  })

  it('moves one invitation to another section without using the registration form', async () => {
    const user = userEvent.setup()
    mocks.reassign.mockResolvedValue({})
    renderPage()
    await user.click(screen.getByRole('button', { name: 'Change section for Ada Lovelace' }))
    const select = screen.getByRole('combobox', { name: 'New section for Ada Lovelace' })
    expect(within(select).queryByRole('option', { name: /Section A/ })).not.toBeInTheDocument()
    await user.selectOptions(select, 'section-2')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(mocks.reassign).toHaveBeenCalledWith('token', 'invite-1', 'section-2')
    await waitFor(() => expect(screen.queryByRole('combobox', { name: /New section/ })).not.toBeInTheDocument())
  })

  it('resends a setup link from the row', async () => {
    const user = userEvent.setup()
    mocks.resend.mockResolvedValue({ delivery_status: 'sent', delivery_message: 'Setup link sent.' })
    renderPage()
    await user.click(screen.getByRole('button', { name: 'Resend link to Grace Hopper' }))
    expect(mocks.resend).toHaveBeenCalledWith('token', 'invite-2')
  })
})

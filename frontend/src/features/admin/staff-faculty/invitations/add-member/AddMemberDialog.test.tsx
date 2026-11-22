import '../../__tests__/StaffFacultyManager.support.ts'
import { CSE } from '../../__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../../StaffFacultyManager.tsx'
import * as api from '../../../../../services/admin/adminApi.ts'

function change(dialog: HTMLElement, label: RegExp, value: string) {
  fireEvent.change(within(dialog).getByLabelText(label), { target: { value } })
}

/** Open Add member and complete step 1 as a Staff member. */
async function basicStaffDetails() {
  render(<StaffFacultyManager accessToken="jwt" />)
  fireEvent.click(await screen.findByRole('button', { name: 'Add member' }))
  const dialog = screen.getByRole('dialog', { name: 'Add Staff or Faculty' })
  change(dialog, /Full name/, 'Sam Rao')
  change(dialog, /Email/, 'sam@example.com')
  change(dialog, /Employee ID/, 'STF-7')
  change(dialog, /Phone/, '+91 98765 43210')
  change(dialog, /Designation/, 'Office Assistant')
  change(dialog, /Joining date/, '2026-06-01')
  fireEvent.click(within(dialog).getByRole('radio', { name: /Staff/ }))
  fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
  return dialog
}

describe('Add Staff or Faculty — staff details and review', () => {
  it('requires a category, a contract end for fixed-term work and a responsibility', async () => {
    const dialog = await basicStaffDetails()
    change(dialog, /Primary department/, CSE.department_id)
    change(dialog, /Employment type/, 'contractual')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).getByText('Choose the staff category.')).toBeInTheDocument()
    expect(within(dialog).getByText('Enter the contract end date for non-permanent employment.')).toBeInTheDocument()
    expect(within(dialog).getByText('Add at least one responsibility.')).toBeInTheDocument()
    expect(within(dialog).getByText(/Step 2 of 3/)).toBeInTheDocument()
    change(dialog, /Contract end date/, '2026-01-01')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).getByText('The contract cannot end before employment starts.')).toBeInTheDocument()
  })

  it('sends only the staff details with the typed and suggested responsibilities', async () => {
    vi.mocked(api.createMembershipInvitation).mockResolvedValue({
      invitation: {} as never,
      email_delivery: { status: 'pending', provider: 'outbox' },
      expires_in_hours: 24,
      message: 'Invitation sent to sam@example.com.',
    })
    const dialog = await basicStaffDetails()
    change(dialog, /Primary department/, CSE.department_id)
    change(dialog, /Staff category/, 'library')
    change(dialog, /Employment type/, 'contractual')
    change(dialog, /Contract end date/, '2027-05-31')
    const responsibility = within(dialog).getByRole('textbox', { name: /Responsibilities/ })
    fireEvent.change(responsibility, { target: { value: '  Issue   desk ' } })
    fireEvent.keyDown(responsibility, { key: 'Enter' })
    fireEvent.click(within(dialog).getByRole('button', { name: '+ Records management' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    const review = within(dialog).getByText('Responsibilities').nextElementSibling
    expect(review).toHaveTextContent('Issue desk, Records management')
    expect(within(dialog).getByText('Library Staff')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Send invitation' }))
    await waitFor(() => expect(api.createMembershipInvitation).toHaveBeenCalled())
    const [, request] = vi.mocked(api.createMembershipInvitation).mock.calls[0]
    expect(request.profile).toEqual({
      common: {
        employee_id: 'STF-7',
        phone: '+91 98765 43210',
        designation: 'Office Assistant',
        joining_date: '2026-06-01',
      },
      staff: {
        employment_type: 'contractual',
        staff_category: 'library',
        employment_start_date: '2026-06-01',
        contract_end_date: '2027-05-31',
        responsibilities: ['Issue desk', 'Records management'],
      },
    })
    expect(request.additional_department_ids).toEqual([])
  })

  it('keeps every value and shows why the server refused', async () => {
    vi.mocked(api.createMembershipInvitation).mockRejectedValue(
      new Error('This employee ID is already used in your institution.'),
    )
    const dialog = await basicStaffDetails()
    change(dialog, /Primary department/, CSE.department_id)
    change(dialog, /Staff category/, 'it_support')
    fireEvent.click(within(dialog).getByRole('button', { name: '+ Student support' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Send invitation' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('employee ID is already used')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Back' }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Back' }))
    expect(within(dialog).getByLabelText(/Employee ID/)).toHaveValue('STF-7')
    expect(within(dialog).queryByRole('alert')).toBeNull()
  })

  it('offers only staff employment types and resets a faculty-only choice', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add member' }))
    const dialog = screen.getByRole('dialog', { name: 'Add Staff or Faculty' })
    change(dialog, /Full name/, 'Ada')
    change(dialog, /Email/, 'ada@example.com')
    change(dialog, /Employee ID/, 'F-1')
    change(dialog, /Designation/, 'Lecturer')
    change(dialog, /Joining date/, '2026-06-01')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).getByRole('option', { name: 'Guest Lecturer' })).toBeInTheDocument()
    change(dialog, /Employment type/, 'guest')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Back' }))
    fireEvent.click(within(dialog).getByRole('radio', { name: /Staff/ }))
    fireEvent.click(within(dialog).getByRole('button', { name: 'Next' }))
    expect(within(dialog).queryByRole('option', { name: 'Guest Lecturer' })).toBeNull()
    expect(within(dialog).getByLabelText(/Employment type/)).toHaveValue('permanent')
  })
})

import { api, catalogue, year, fillYear, openCreate, renderCalendar } from './Calendar.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

describe('Academic calendar editor', () => {
  it('uses the latest record when switching from details to editing after a refresh', async () => {
    renderCalendar()
    fireEvent.click(await screen.findByRole('button', { name: `View ${year.name}` }, { timeout: 5000 }))
    catalogue.records.academic_years![0].name = 'Refreshed academic year'
    const { queryClient } = await import('../../../../../lib/queryClient.ts')
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ['admin', 'academic-overview'] })
    })
    await screen.findByRole('article', { name: 'Refreshed academic year', hidden: true }, { timeout: 5000 })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Edit Academic Year', exact: true })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Edit Academic Year', exact: true }))
    expect(screen.getByRole('dialog', { name: 'Edit Academic Year' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Academic Year Name/)).toHaveValue('Refreshed academic year')
  })

  it('validates required fields, year dates and initial semesters before saving', async () => {
    renderCalendar()
    await openCreate()
    fireEvent.change(screen.getByLabelText(/Academic Year Name/), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText(/Academic Year Code/), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    expect(screen.getByText('Enter a name.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Academic Year Name/)).toHaveFocus()
    fillYear()
    fireEvent.change(screen.getByLabelText('End Date *', { selector: '#calendar-end' }), {
      target: { value: '2028-07-01' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    expect(screen.getByText('End date must be after start date.')).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('creates a year and initial dated semesters through the existing API', async () => {
    renderCalendar()
    await openCreate()
    fillYear()
    fireEvent.click(screen.getByRole('radio', { name: '3 Semesters (Trimester)' }))
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    await screen.findByText('Academic year created successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(4)
    expect(api.createAcademicRecord).toHaveBeenNthCalledWith(1, 'token-1', 'academic_years', {
      name: '2028 - 2029',
      code: 'AY2028',
      start_date: '2028-08-01',
      end_date: '2029-07-31',
      is_active: true,
      is_current: false,
    })
    const saved = catalogue.records.semesters!.filter((item) => item.academic_year_id === 'created-1')
    expect(saved).toHaveLength(3)
    expect(saved[0].start_date).toBe('2028-08-01')
    expect(saved[2].end_date).toBe('2029-07-31')
  })

  it('confirms discarding a draft and restores focus to the opener', async () => {
    renderCalendar()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Academic Year', exact: true })).toBeEnabled())
    const trigger = screen.getByRole('button', { name: 'Add Academic Year', exact: true })
    trigger.focus()
    await openCreate()
    fillYear()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    expect(screen.getByRole('alertdialog', { name: 'Discard your changes?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Keep Editing' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByLabelText(/Academic Year Code/)).toHaveValue(' AY2028 ')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
    expect(trigger).toHaveFocus()
  })

  it('edits status with confirmation and preserves the immutable semester parent', async () => {
    renderCalendar()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit Semester 1', exact: true }))
    const dialog = screen.getByRole('dialog', { name: 'Edit Semester' })
    expect(within(dialog).getByRole('combobox', { name: /Academic Year/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Set as current semester' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Changes' }))
    await screen.findByText('Semester updated successfully.')
    expect(api.updateAcademicRecord).toHaveBeenCalledWith(
      'token-1',
      'semesters',
      'semester-1',
      expect.objectContaining({ is_current: false }),
    )
    expect(vi.mocked(api.updateAcademicRecord).mock.calls[0][3]).not.toHaveProperty('academic_year_id')
  })

  it('adds a semester to its selected year and rejects dates outside that year', async () => {
    renderCalendar()
    fireEvent.click(await screen.findByRole('button', { name: 'Add Semester', exact: true }))
    expect(screen.getByRole('combobox', { name: /Academic Year/ })).toHaveValue(year.academic_year_id)
    fireEvent.change(screen.getByLabelText('End Date *', { selector: '#calendar-end' }), {
      target: { value: '2028-01-01' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create Semester' }))
    expect(screen.getByText('Semester dates must fall within the academic year.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('End Date *', { selector: '#calendar-end' }), {
      target: { value: '2027-06-30' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create Semester' }))
    await screen.findByText('Semester created successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledWith(
      'token-1',
      'semesters',
      expect.objectContaining({ academic_year_id: year.academic_year_id, semester_number: 3 }),
    )
  })
})

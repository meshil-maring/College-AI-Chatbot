import { api, catalogue, program, fillProgram, openCreate, renderPrograms } from './Programs.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { DegreeProgram } from '../../../../../types/academicSetup.ts'

describe('Program drawers', () => {
  it('validates required fields and focuses the first error', async () => {
    renderPrograms()
    await openCreate()
    expect(screen.getByRole('radio', { name: /^Active/ })).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Create Program' }))
    expect(screen.getByText('Enter a program name.')).toBeInTheDocument()
    expect(screen.getByText('Enter a program code.')).toBeInTheDocument()
    expect(screen.getByText('Select a department.')).toBeInTheDocument()
    expect(screen.getByText('Select a degree type.')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /Program Name/ })).toHaveFocus()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('creates through the existing service with trimmed text, fractional duration and optional credits', async () => {
    renderPrograms()
    await openCreate()
    fillProgram()
    fireEvent.change(screen.getByRole('spinbutton', { name: /Total Credits/ }), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Program' }))
    await screen.findByText('Program created successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledWith('token-1', 'programs', {
      name: 'Applied Mathematics',
      code: 'AM',
      department_id: 'department-1',
      degree_type: 'B.Sc',
      duration_years: 3.5,
      total_credits: 0,
      description: null,
      is_active: true,
    })
    expect(await screen.findByRole('row', { name: /Applied Mathematics/ })).toBeInTheDocument()
  })

  it('keeps entries and focuses the code after a duplicate conflict', async () => {
    vi.mocked(api.createAcademicRecord).mockRejectedValueOnce(
      new AdminApiError(409, 'Duplicate', undefined, 'ACADEMIC_DUPLICATE'),
    )
    renderPrograms()
    await openCreate()
    fillProgram()
    fireEvent.click(screen.getByRole('button', { name: 'Create Program' }))
    await screen.findByText('This program code is already in use in your institution.')
    expect(screen.getByRole('textbox', { name: /Program Code/ })).toHaveFocus()
    expect(screen.getByRole('textbox', { name: /Program Name/ })).toHaveValue(' Applied Mathematics ')
    fireEvent.change(screen.getByRole('textbox', { name: /Program Code/ }), { target: { value: 'AM2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Program' }))
    expect(await screen.findByText('Program created successfully.')).toBeInTheDocument()
  })

  it('confirms discarding and restores the invoking control after closing', async () => {
    renderPrograms()
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Add Program', exact: true })[0]).toBeEnabled())
    const trigger = screen.getAllByRole('button', { name: 'Add Program', exact: true })[0]
    trigger.focus()
    await openCreate()
    fillProgram()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    const confirmation = screen.getByRole('alertdialog', { name: 'Discard your changes?' })
    expect(within(confirmation).getByRole('button', { name: 'Keep Editing' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByRole('textbox', { name: /Program Name/ })).toHaveValue(' Applied Mathematics ')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('preserves custom degree types, keeps the department immutable and confirms status changes', async () => {
    catalogue.records.programs = [{ ...program, degree_type: 'Custom degree', duration_years: 2.5 }]
    renderPrograms()
    fireEvent.click(await screen.findByRole('button', { name: `View ${program.name}` }))
    expect(screen.getByRole('dialog', { name: 'Program details' })).toHaveTextContent('Custom degree')
    fireEvent.click(screen.getByRole('button', { name: 'Edit Program', exact: true }))
    const form = within(screen.getByRole('form', { name: 'Edit degree program' }))
    expect(form.getByRole('combobox', { name: /^Department/ })).toBeDisabled()
    expect(form.getByRole('combobox', { name: /Degree Type/ })).toHaveValue('Custom degree')
    fireEvent.click(screen.getByRole('radio', { name: /^Inactive/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(screen.getByRole('alertdialog', { name: 'Confirm status change' })).toBeInTheDocument()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Changes' }))
    await screen.findByText('Program updated successfully.')
    const payload = vi.mocked(api.updateAcademicRecord).mock.calls[0][3]
    expect(payload).not.toHaveProperty('department_id')
    expect(payload).toMatchObject({ is_active: false, degree_type: 'Custom degree', duration_years: 2.5 })
  })

  it('prevents duplicate submissions and retains entries after a network error', async () => {
    let reject!: (cause: Error) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<DegreeProgram>((_resolve, fail) => {
          reject = fail
        }),
    )
    renderPrograms()
    await openCreate()
    fillProgram()
    fireEvent.click(screen.getByRole('button', { name: 'Create Program' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled())
    expect(screen.getByRole('textbox', { name: /Program Name/ })).toBeDisabled()
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    await act(async () => reject(new Error('Service unavailable.')))
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable.')
    expect(screen.getByRole('textbox', { name: /Program Name/ })).toHaveValue(' Applied Mathematics ')
  })
})

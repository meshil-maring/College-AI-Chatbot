import { api, subject, fillSubject, openCreate, renderSubjects } from './Subjects.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { Course } from '../../../../../types/academicSetup.ts'

describe('Subject drawers', () => {
  it('validates required text and department and focuses the first error', async () => {
    renderSubjects()
    await openCreate()
    expect(screen.getByRole('radio', { name: /^Active/ })).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    expect(screen.getByText('Enter a subject name.')).toBeInTheDocument()
    expect(screen.getByText('Enter a subject code.')).toBeInTheDocument()
    expect(screen.getByText('Select a department.')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /Subject Name/ })).toHaveFocus()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('creates a reusable subject with trimmed text, fractional credits and nullable hours', async () => {
    renderSubjects()
    await openCreate()
    fillSubject()
    fireEvent.change(screen.getByRole('spinbutton', { name: /Credits/ }), { target: { value: '3.5' } })
    fireEvent.change(screen.getByRole('spinbutton', { name: /Tutorial Hours/ }), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    await screen.findByText('Subject created successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledWith('token-1', 'courses', {
      name: 'Applied Mathematics',
      code: 'AM',
      department_id: 'department-1',
      credits: 3.5,
      lecture_hours: 3,
      tutorial_hours: null,
      practical_hours: 0,
      description: null,
      is_active: true,
    })
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('row', { name: /Applied Mathematics/ })).toHaveTextContent('Unassigned')
  })

  it('rejects non-positive credits and negative hours while preserving the draft', async () => {
    renderSubjects()
    await openCreate()
    fillSubject()
    fireEvent.change(screen.getByRole('spinbutton', { name: /Credits/ }), { target: { value: '0' } })
    fireEvent.change(screen.getByRole('spinbutton', { name: /Practical Hours/ }), { target: { value: '-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    expect(screen.getByRole('spinbutton', { name: /Credits/ })).toHaveFocus()
    expect(screen.getByText('Enter zero or a positive number, or leave blank.')).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('retains entries after a duplicate conflict and permits correction', async () => {
    vi.mocked(api.createAcademicRecord).mockRejectedValueOnce(
      new AdminApiError(409, 'Duplicate', undefined, 'ACADEMIC_DUPLICATE'),
    )
    renderSubjects()
    await openCreate()
    fillSubject()
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    await screen.findByText('This subject code is already in use in your institution.')
    expect(screen.getByRole('textbox', { name: /Subject Code/ })).toHaveFocus()
    expect(screen.getByRole('textbox', { name: /Subject Name/ })).toHaveValue(' Applied Mathematics ')
    fireEvent.change(screen.getByRole('textbox', { name: /Subject Code/ }), { target: { value: 'AM2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    expect(await screen.findByText('Subject created successfully.')).toBeInTheDocument()
  })

  it('confirms discarding edits and restores focus to the invoking control', async () => {
    renderSubjects()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Subject', exact: true })).toBeEnabled())
    const trigger = screen.getByRole('button', { name: 'Add Subject', exact: true })
    trigger.focus()
    await openCreate()
    fillSubject()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    expect(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Keep Editing' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByRole('textbox', { name: /Subject Name/ })).toHaveValue(' Applied Mathematics ')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('shows assignment details and preserves the immutable department and null values on edit', async () => {
    renderSubjects()
    fireEvent.click(await screen.findByRole('button', { name: `View ${subject.name}` }))
    expect(screen.getByRole('dialog', { name: 'Subject details' })).toHaveTextContent('Core')
    fireEvent.click(screen.getByRole('button', { name: 'Edit Subject', exact: true }))
    const form = within(screen.getByRole('form', { name: 'Edit subject' }))
    expect(form.getByRole('combobox', { name: /^Department/ })).toBeDisabled()
    expect(screen.getByRole('spinbutton', { name: /Tutorial Hours/ })).toHaveValue(null)
    fireEvent.click(screen.getByRole('radio', { name: /^Inactive/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(screen.getByRole('alertdialog', { name: 'Confirm status change' })).toBeInTheDocument()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Changes' }))
    await screen.findByText('Subject updated successfully.')
    const payload = vi.mocked(api.updateAcademicRecord).mock.calls[0][3]
    expect(payload).not.toHaveProperty('department_id')
    expect(payload).toMatchObject({ is_active: false, credits: 3.5, tutorial_hours: null })
  })

  it('prevents duplicate submission and keeps entries after a network failure', async () => {
    let reject!: (cause: Error) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<Course>((_resolve, fail) => {
          reject = fail
        }),
    )
    renderSubjects()
    await openCreate()
    fillSubject()
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled())
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('textbox', { name: /Subject Name/ })).toBeDisabled()
    await act(async () => reject(new Error('Service unavailable.')))
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable.')
    expect(screen.getByRole('textbox', { name: /Subject Name/ })).toHaveValue(' Applied Mathematics ')
  })
})

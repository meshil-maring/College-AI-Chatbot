import {
  api,
  catalogue,
  course,
  extraCourse,
  link,
  program,
  semester,
  chooseSubject,
  openMapping,
  renderCurriculum,
  loaded,
} from './Curriculum.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { ProgramCourse } from '../../../../../types/academicSetup.ts'

describe('Curriculum subject mapping editor', () => {
  it('validates the subject and creates only an existing program-course relationship', async () => {
    renderCurriculum()
    const drawer = await openMapping()
    fireEvent.click(drawer.getByRole('button', { name: 'Add Subject', exact: true }))
    expect(screen.getByText('Select a subject.')).toBeInTheDocument()
    expect(drawer.getByRole('combobox', { name: 'Subject', exact: true })).toHaveFocus()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
    chooseSubject()
    fireEvent.change(drawer.getByRole('combobox', { name: 'Subject Type' }), { target: { value: 'elective' } })
    fireEvent.click(drawer.getByRole('checkbox', { name: 'Required subject' }))
    fireEvent.click(drawer.getByRole('button', { name: 'Add Subject', exact: true }))
    await screen.findByText('Subject mapped successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledWith('token-1', 'program_courses', {
      program_id: program.program_id,
      course_id: extraCourse.course_id,
      semester_id: semester.semester_id,
      course_type: 'elective',
      is_required: false,
      is_active: true,
    })
    expect(await screen.findByRole('row', { name: /Computer Vision/ })).toHaveTextContent('Elective')
  })

  it('allows mappings for all semesters without inventing a progression stage', async () => {
    renderCurriculum()
    const drawer = await openMapping()
    chooseSubject()
    fireEvent.change(drawer.getByRole('combobox', { name: 'Academic Term (Optional)' }), { target: { value: '' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Add Subject', exact: true }))
    await screen.findByText('Subject mapped successfully.')
    expect(vi.mocked(api.createAcademicRecord).mock.calls[0][2]).toMatchObject({ semester_id: null })
  })

  it('edits type and required status while preserving immutable relationships', async () => {
    renderCurriculum()
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: `Edit mapping for ${course.name}` }))
    const drawer = within(screen.getByRole('dialog', { name: 'Edit Subject Mapping' }))
    expect(drawer.getByRole('combobox', { name: 'Subject', exact: true })).toBeDisabled()
    expect(drawer.getByRole('combobox', { name: 'Academic Term (Optional)' })).toBeDisabled()
    fireEvent.change(drawer.getByRole('combobox', { name: 'Subject Type' }), { target: { value: 'project' } })
    fireEvent.click(drawer.getByRole('checkbox', { name: 'Required subject' }))
    fireEvent.click(drawer.getByRole('button', { name: 'Save Changes' }))
    await screen.findByText('Subject mapping updated successfully.')
    expect(api.updateAcademicRecord).toHaveBeenCalledWith('token-1', 'program_courses', link.program_course_id, {
      course_type: 'project',
      is_required: false,
      is_active: true,
    })
  })

  it('confirms deactivation and retains mapping records', async () => {
    renderCurriculum()
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: `Deactivate mapping for ${course.name}` }))
    expect(screen.getByRole('alertdialog', { name: 'Confirm mapping status change' })).toHaveTextContent(
      'Existing records will be retained',
    )
    expect(screen.getByRole('button', { name: 'Keep Editing' })).toHaveFocus()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Changes' }))
    await screen.findByText('Subject mapping updated successfully.')
    expect(vi.mocked(api.updateAcademicRecord).mock.calls[0][3]).toMatchObject({ is_active: false })
    expect(screen.getByRole('row', { name: /Data Mining/ })).toHaveTextContent('Inactive')
  })

  it('keeps entries after duplicate conflicts', async () => {
    vi.mocked(api.createAcademicRecord).mockRejectedValueOnce(
      new AdminApiError(409, 'Duplicate', undefined, 'ACADEMIC_DUPLICATE'),
    )
    renderCurriculum()
    const drawer = await openMapping()
    chooseSubject()
    fireEvent.click(drawer.getByRole('button', { name: 'Add Subject', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This subject mapping already exists')
    expect(drawer.getByRole('combobox', { name: 'Subject', exact: true })).toHaveValue(extraCourse.course_id)
  })

  it('prevents duplicate submissions and retains entries after a network failure', async () => {
    let reject!: (cause: Error) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<ProgramCourse>((_resolve, fail) => {
          reject = fail
        }),
    )
    renderCurriculum()
    const drawer = await openMapping()
    chooseSubject()
    fireEvent.click(drawer.getByRole('button', { name: 'Add Subject', exact: true }))
    await waitFor(() => expect(drawer.getByRole('button', { name: 'Saving…' })).toBeDisabled())
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    await act(async () => reject(new Error('Service unavailable.')))
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable.')
    expect(drawer.getByRole('combobox', { name: 'Subject', exact: true })).toHaveValue(extraCourse.course_id)
  })

  it('confirms discarding changes and restores the invoking control', async () => {
    renderCurriculum()
    await loaded()
    const trigger = screen.getByRole('button', { name: 'Add Subject', exact: true })
    trigger.focus()
    const drawer = await openMapping()
    chooseSubject()
    fireEvent.click(drawer.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByRole('combobox', { name: 'Subject', exact: true })).toHaveValue(extraCourse.course_id)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('offers only active, institution-scoped subjects and terms with active ancestors', async () => {
    catalogue.records.courses!.push(
      { ...extraCourse, course_id: 'inactive', name: 'Inactive Subject', is_active: false },
      { ...extraCourse, course_id: 'foreign', name: 'Foreign Subject', institution_id: 'foreign' },
    )
    catalogue.records.semesters!.push({
      ...semester,
      semester_id: 'bad-term',
      name: 'Other Year',
      academic_year_id: 'missing-year',
    })
    renderCurriculum()
    const drawer = await openMapping()
    expect(
      drawer.queryByRole('option', { name: /Inactive Subject|Foreign Subject|Other Year/ }),
    ).not.toBeInTheDocument()
    expect(drawer.getByRole('option', { name: /Computer Vision/ })).toBeInTheDocument()
  })
})

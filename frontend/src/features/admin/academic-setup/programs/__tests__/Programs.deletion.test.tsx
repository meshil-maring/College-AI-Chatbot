import { api, auth, catalogue, program, renderPrograms, Workspace, setCatalogue } from './Programs.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { DegreeProgram } from '../../../../../types/academicSetup.ts'

beforeEach(() => {
  catalogue.records.programs = [structuredClone(program)]
})

async function openDeletion() {
  const trigger = await screen.findByRole('button', { name: `Delete ${program.name}` })
  trigger.focus()
  fireEvent.click(trigger)
  return screen.findByRole('alertdialog', { name: 'Delete program?' })
}

describe('Program deletion', () => {
  it('requires confirmation, focuses Cancel and restores the opener on cancellation', async () => {
    renderPrograms()
    const dialog = await openDeletion()
    expect(within(dialog).getByText(/cannot be undone/)).toBeInTheDocument()
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' })
    expect(cancel).toHaveFocus()
    fireEvent.click(cancel)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Delete ${program.name}` })).toHaveFocus()
    expect(api.deleteProgram).not.toHaveBeenCalled()
  })

  it('deletes once, guards pending actions and refreshes the program list', async () => {
    let resolve!: (value: DegreeProgram) => void
    vi.mocked(api.deleteProgram).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    renderPrograms()
    const dialog = await openDeletion()
    const confirm = within(dialog).getByRole('button', { name: 'Delete Program' })
    fireEvent.click(confirm)
    fireEvent.click(confirm)
    await waitFor(() => expect(api.deleteProgram).toHaveBeenCalledTimes(1))
    expect(api.deleteProgram).toHaveBeenCalledWith('token-1', program.program_id)
    expect(within(dialog).getByRole('button', { name: 'Deleting…' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled()
    fireEvent(dialog, new Event('cancel', { cancelable: true }))
    expect(dialog).toBeInTheDocument()
    catalogue.records.programs = []
    await act(async () => resolve(program))
    expect(await screen.findByText('Program deleted successfully.')).toBeInTheDocument()
    expect(await screen.findByText('No programs yet')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Programs', level: 1 })).toHaveFocus()
    expect(catalogue.records.departments).toHaveLength(1)
    expect(api.deleteDepartment).not.toHaveBeenCalled()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(2)
  })

  it.each([true, false])('blocks subject mappings with active status %s', async (active) => {
    catalogue.records.program_courses = [
      {
        program_course_id: 'mapping-1',
        institution_id: program.institution_id,
        program_id: program.program_id,
        course_id: 'course-1',
        semester_id: null,
        course_type: 'core',
        is_required: true,
        is_active: active,
      },
    ]
    renderPrograms()
    const dialog = await openDeletion()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('linked subject mappings, including inactive records')
    expect(within(dialog).getByRole('button', { name: 'Delete Program' })).toBeDisabled()
    expect(api.deleteProgram).not.toHaveBeenCalled()
  })

  it('blocks inactive course offerings', async () => {
    catalogue.records.course_offerings = [
      {
        course_offering_id: 'offering-1',
        institution_id: program.institution_id,
        program_id: program.program_id,
        course_id: 'course-1',
        semester_id: 'term-1',
        academic_year_id: 'year-1',
        capacity: null,
        is_active: false,
      },
    ]
    renderPrograms()
    const dialog = await openDeletion()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('linked course offerings')
    expect(within(dialog).getByRole('button', { name: 'Delete Program' })).toBeDisabled()
  })

  it('shows server conflicts for curriculum or batch links absent from the catalogue', async () => {
    vi.mocked(api.deleteProgram).mockRejectedValueOnce(
      new AdminApiError(
        409,
        'This program cannot be deleted because it has linked curricula, including inactive records.',
        undefined,
        'PROGRAM_IN_USE',
      ),
    )
    renderPrograms()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Program' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('linked curricula')
    expect(catalogue.records.programs).toHaveLength(1)
    expect(screen.queryByText('Program deleted successfully.')).not.toBeInTheDocument()
  })

  it('can retry deletion of an unused inactive program even with an inactive department', async () => {
    catalogue.records.programs![0].is_active = false
    catalogue.records.departments![0].is_active = false
    vi.mocked(api.deleteProgram)
      .mockRejectedValueOnce(new Error('Network unavailable'))
      .mockImplementationOnce(async () => {
        catalogue.records.programs = []
        return { ...program, is_active: false }
      })
    renderPrograms()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Program' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Network unavailable')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Program' }))
    expect(await screen.findByText('Program deleted successfully.')).toBeInTheDocument()
    expect(api.deleteProgram).toHaveBeenCalledTimes(2)
  })

  it('does not offer deletion to a read-only user', async () => {
    catalogue.manageable = []
    renderPrograms()
    await screen.findByRole('button', { name: `View ${program.name}` })
    expect(screen.queryByRole('button', { name: /^Delete/ })).not.toBeInTheDocument()
  })

  it('ignores late responses after replacing the institution identity', async () => {
    let resolve!: (value: DegreeProgram) => void
    vi.mocked(api.deleteProgram).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const page = renderPrograms()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Program' }))
    await waitFor(() => expect(api.deleteProgram).toHaveBeenCalledTimes(1))
    auth.accessToken = 'replacement-token'
    auth.user.institution_id = 'replacement-institution'
    setCatalogue({
      institution_id: 'replacement-institution',
      records: { programs: [], departments: [] },
      manageable: [],
    })
    page.rerender(<Workspace />)
    expect(await screen.findByText('No programs yet')).toBeInTheDocument()
    const requests = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve(program))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.queryByText('Program deleted successfully.')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(requests)
  })

  it('rejects a response from a different institution', async () => {
    vi.mocked(api.deleteProgram).mockResolvedValueOnce({ ...program, institution_id: 'foreign' })
    renderPrograms()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Program' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('could not be verified')
  })
})

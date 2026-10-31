import { api, auth, catalogue, year, semester, renderCalendar, Workspace, setCatalogue } from './Calendar.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AcademicYear } from '../../../../../types/academicSetup.ts'
import { AdminApiError } from '../../../../../services/admin/http.ts'

async function openDelete(name: string, kind: string) {
  fireEvent.click(await screen.findByRole('button', { name: `Delete ${name}`, exact: true }))
  return screen.findByRole('alertdialog', { name: `Delete ${kind}?` })
}
describe('Calendar deletion', () => {
  it('confirms deletion of an unused year, refreshes the list and preserves other years', async () => {
    vi.mocked(api.deleteAcademicYear).mockImplementationOnce(async () => {
      const selected = catalogue.records.academic_years![1]
      catalogue.records.academic_years!.splice(1, 1)
      return selected
    })
    renderCalendar()
    const dialog = await openDelete('2024 - 2025', 'academic year')
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus()
    expect(api.deleteAcademicYear).not.toHaveBeenCalled()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Academic Year' }))
    expect(await screen.findByText('Academic Year deleted successfully.')).toBeInTheDocument()
    expect(api.deleteAcademicYear).toHaveBeenCalledWith('token-1', 'year-2')
    expect(screen.queryByRole('button', { name: 'Delete 2024 - 2025' })).not.toBeInTheDocument()
    expect(catalogue.records.academic_years).toHaveLength(1)
    vi.mocked(api.deleteSemester).mockImplementationOnce(async () => {
      const selected = catalogue.records.semesters![1]
      catalogue.records.semesters!.splice(1, 1)
      return selected
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Semesters', exact: true }))
    const nextDialog = await openDelete('Semester 2', 'semester')
    fireEvent.click(within(nextDialog).getByRole('button', { name: 'Delete Semester' }))
    expect(await screen.findByText('Semester deleted successfully.')).toBeInTheDocument()
    expect(screen.queryByText('Academic Year deleted successfully.')).not.toBeInTheDocument()
  })

  it('blocks a current year before deletion, regardless of linked records', async () => {
    renderCalendar()
    const dialog = await openDelete(year.name, 'academic year')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('replacement current academic year or semester')
    expect(within(dialog).getByRole('button', { name: 'Delete Academic Year' })).toBeDisabled()
    expect(api.deleteAcademicYear).not.toHaveBeenCalled()
  })

  it('blocks an inactive semester linked to a non-current year', async () => {
    catalogue.records.academic_years![0].is_current = false
    catalogue.records.semesters![0].is_active = false
    catalogue.records.semesters![0].is_current = false
    renderCalendar()
    const dialog = await openDelete(year.name, 'academic year')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('linked semesters, including inactive records')
    expect(within(dialog).getByRole('button', { name: 'Delete Academic Year' })).toBeDisabled()
  })

  it('deletes a non-current semester after confirmation while retaining its year', async () => {
    vi.mocked(api.deleteSemester).mockImplementationOnce(async () => {
      const selected = catalogue.records.semesters![1]
      catalogue.records.semesters!.splice(1, 1)
      return selected
    })
    renderCalendar()
    fireEvent.click(await screen.findByRole('tab', { name: 'Semesters', exact: true }))
    const dialog = await openDelete('Semester 2', 'semester')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Semester' }))
    expect(await screen.findByText('Semester deleted successfully.')).toBeInTheDocument()
    expect(api.deleteSemester).toHaveBeenCalledWith('token-1', 'semester-2')
    expect(catalogue.records.academic_years).toHaveLength(2)
  })

  it('blocks the current semester', async () => {
    renderCalendar()
    fireEvent.click(await screen.findByRole('tab', { name: 'Semesters', exact: true }))
    const dialog = await openDelete(semester.name, 'semester')
    expect(within(dialog).getByRole('button', { name: 'Delete Semester' })).toBeDisabled()
    expect(api.deleteSemester).not.toHaveBeenCalled()
  })

  it('keeps a semester when server-only student registrations block deletion', async () => {
    vi.mocked(api.deleteSemester).mockRejectedValueOnce(
      new AdminApiError(
        409,
        'This semester has linked student assignments or registrations, including inactive records.',
        undefined,
        'SEMESTER_IN_USE',
      ),
    )
    renderCalendar()
    fireEvent.click(await screen.findByRole('tab', { name: 'Semesters', exact: true }))
    const dialog = await openDelete('Semester 2', 'semester')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Semester' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('student assignments or registrations')
    expect(catalogue.records.semesters).toHaveLength(2)
  })

  it('hides deletion for read-only users', async () => {
    catalogue.manageable = []
    renderCalendar()
    await screen.findByRole('button', { name: `View ${year.name}` })
    expect(screen.queryByRole('button', { name: /^Delete/ })).not.toBeInTheDocument()
  })

  it('guards duplicate submissions and ignores late results after institution replacement', async () => {
    let resolve!: (record: AcademicYear) => void
    vi.mocked(api.deleteAcademicYear).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const page = renderCalendar()
    const dialog = await openDelete('2024 - 2025', 'academic year')
    const button = within(dialog).getByRole('button', { name: 'Delete Academic Year' })
    fireEvent.click(button)
    fireEvent.click(button)
    await waitFor(() => expect(api.deleteAcademicYear).toHaveBeenCalledTimes(1))
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled()
    auth.accessToken = 'replacement-token'
    auth.user.institution_id = 'replacement'
    setCatalogue({ institution_id: 'replacement', records: { academic_years: [] }, manageable: [] })
    page.rerender(<Workspace />)
    await screen.findByText('No academic years yet')
    const requests = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve({ ...year, academic_year_id: 'year-2' }))
    expect(screen.queryByText('Academic Year deleted successfully.')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(requests)
  })
})

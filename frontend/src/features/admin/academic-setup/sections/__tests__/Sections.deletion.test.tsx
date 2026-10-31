import { api, auth, structureCatalogue, section, renderSections, Workspace } from './Sections.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AcademicSection } from '../../../../../types/academicStructure.ts'
import { AdminApiError } from '../../../../../services/admin/http.ts'

beforeEach(() => {
  structureCatalogue.records.academic_offerings = []
})
async function openDelete() {
  const button = await screen.findByRole('button', { name: /^Delete .*Section A/ })
  button.focus()
  fireEvent.click(button)
  return screen.findByRole('alertdialog', { name: 'Delete section?' })
}
describe('Class-section deletion', () => {
  it('allows cancellation and restores focus without a request', async () => {
    renderSections()
    const dialog = await openDelete()
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' })
    expect(cancel).toHaveFocus()
    fireEvent.click(cancel)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Delete .*Section A/ })).toHaveFocus()
    expect(api.deleteAcademicSection).not.toHaveBeenCalled()
  })

  it('deletes an unused section once and refreshes its structure catalogue', async () => {
    vi.mocked(api.deleteAcademicSection).mockImplementationOnce(async () => {
      structureCatalogue.records.academic_sections = []
      return section
    })
    renderSections()
    const dialog = await openDelete()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Section' }))
    expect(await screen.findByText('Section deleted successfully.')).toBeInTheDocument()
    expect(api.deleteAcademicSection).toHaveBeenCalledWith('token-1', section.academic_section_id)
    expect(await screen.findByText('No sections found')).toBeInTheDocument()
    expect(structureCatalogue.records.admission_cohorts).toHaveLength(1)
    expect(screen.getByRole('heading', { name: 'Sections', level: 1 })).toHaveFocus()
  })

  it.each([true, false])('blocks a linked subject offering with active status %s', async (active) => {
    structureCatalogue.records.academic_offerings = [
      {
        academic_offering_id: 'offering-1',
        academic_section_id: section.academic_section_id,
        curriculum_subject_id: 'mapping-1',
        capacity: 60,
        institution_id: section.institution_id,
        is_active: active,
        created_at: section.created_at,
        updated_at: section.updated_at,
      },
    ]
    renderSections()
    const dialog = await openDelete()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('linked subject offerings, including inactive records')
    expect(within(dialog).getByRole('button', { name: 'Delete Section' })).toBeDisabled()
  })

  it('preserves student-linked sections when the backend rejects deletion', async () => {
    vi.mocked(api.deleteAcademicSection).mockRejectedValueOnce(
      new AdminApiError(
        409,
        'This section has linked student assignments or registrations, including inactive records.',
        undefined,
        'SECTION_IN_USE',
      ),
    )
    renderSections()
    const dialog = await openDelete()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Section' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('student assignments or registrations')
    expect(structureCatalogue.records.academic_sections).toHaveLength(1)
  })

  it('does not expose deletion with read-only grants', async () => {
    structureCatalogue.manageable = []
    renderSections()
    await screen.findByRole('button', { name: /^View .*Section A/ })
    expect(screen.queryByRole('button', { name: /^Delete/ })).not.toBeInTheDocument()
  })

  it('guards pending requests and ignores late success after identity replacement', async () => {
    let resolve!: (value: AcademicSection) => void
    vi.mocked(api.deleteAcademicSection).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const page = renderSections()
    const dialog = await openDelete()
    const button = within(dialog).getByRole('button', { name: 'Delete Section' })
    fireEvent.click(button)
    fireEvent.click(button)
    await waitFor(() => expect(api.deleteAcademicSection).toHaveBeenCalledTimes(1))
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled()
    auth.accessToken = 'replacement'
    auth.user.institution_id = 'replacement'
    page.rerender(<Workspace />)
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
    await act(async () => resolve(section))
    expect(screen.queryByText('Section deleted successfully.')).not.toBeInTheDocument()
  })
})

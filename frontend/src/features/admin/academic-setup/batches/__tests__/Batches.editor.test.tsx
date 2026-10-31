import { api, fillBatch, openAdd, renderBatches } from './Batches.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

describe('Batch database editor', () => {
  it('creates a persisted batch with published curriculum and keeps capacity separate from enrollment', async () => {
    renderBatches()
    const drawer = await openAdd()
    expect(drawer.getByRole('textbox', { name: 'Batch Name' })).toHaveFocus()
    fillBatch()
    fireEvent.change(drawer.getByLabelText('Expected Student Count (Optional)'), { target: { value: '90' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Create Batch' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'admission_cohorts',
      expect.objectContaining({
        program_id: 'program-1',
        curriculum_version_id: 'version-1',
        academic_year_id: 'year-1',
        expected_count: 90,
        name: 'CSE Summer',
      }),
    )
    expect(screen.getByRole('button', { name: 'View CSE Summer' }).closest('tr')).toHaveTextContent('Unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Set up sections' }))
    expect(await screen.findByRole('heading', { name: 'Sections', level: 1 })).toBeInTheDocument()
  })
  it('retains drafts after API errors and prevents duplicate submissions', async () => {
    let reject!: (error: Error) => void
    vi.mocked(api.createStructureRecord).mockImplementationOnce(
      () =>
        new Promise((_resolve, fail) => {
          reject = fail
        }),
    )
    renderBatches()
    const drawer = await openAdd()
    fillBatch()
    const submit = drawer.getByRole('button', { name: 'Create Batch' })
    fireEvent.click(submit)
    fireEvent.click(submit)
    await waitFor(() => expect(api.createStructureRecord).toHaveBeenCalledTimes(1))
    expect(submit).toBeDisabled()
    reject(new Error('Database conflict'))
    expect(await drawer.findByRole('alert')).toHaveTextContent('Database conflict')
    expect(drawer.getByRole('textbox', { name: 'Batch Name' })).toHaveValue('CSE Summer')
  })
  it('retains immutable parent assignments on edits and confirms status changes', async () => {
    renderBatches()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit CSE 2026' }))
    const drawer = within(screen.getByRole('dialog', { name: 'Edit Batch' }))
    expect(drawer.getByRole('combobox', { name: 'Program' })).toBeDisabled()
    expect(drawer.getByRole('combobox', { name: 'Curriculum Version' })).toBeDisabled()
    expect(drawer.getByRole('spinbutton', { name: 'Start Year' })).toBeDisabled()
    fireEvent.click(drawer.getByRole('radio', { name: /^Completed/ }))
    fireEvent.click(drawer.getByRole('button', { name: 'Save Changes' }))
    expect(screen.getByRole('alertdialog', { name: 'Change batch status?' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Change' }))
    await waitFor(() =>
      expect(api.updateStructureRecord).toHaveBeenCalledWith(
        'token-1',
        'admission_cohorts',
        'cohort-1',
        expect.objectContaining({ status: 'completed' }),
      ),
    )
    expect(vi.mocked(api.updateStructureRecord).mock.calls[0][3]).not.toHaveProperty('curriculum_version_id')
  })
  it('confirms unsaved draft discard and restores focus', async () => {
    renderBatches()
    const drawer = await openAdd()
    fireEvent.change(drawer.getByRole('textbox', { name: 'Batch Name' }), { target: { value: 'Pending' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('alertdialog', { name: 'Discard your changes?' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByRole('textbox', { name: 'Batch Name' })).toHaveValue('Pending')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
    expect(api.createStructureRecord).not.toHaveBeenCalled()
  })
})

import { api, fillSection, openAdd, renderSections } from './Sections.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

describe('Section database editor', () => {
  it('creates a section with an immutable batch, program stage and dated teaching term', async () => {
    renderSections()
    const drawer = await openAdd()
    fillSection()
    expect(drawer.getByRole('textbox', { name: 'Program' })).toHaveValue('B.Tech CSE')
    expect(drawer.getByRole('textbox', { name: 'Batch Academic Year' })).toBeDisabled()
    fireEvent.change(drawer.getByLabelText('Maximum Capacity (Optional)'), { target: { value: '60' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Create Section' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'academic_sections',
      expect.objectContaining({
        admission_cohort_id: 'cohort-1',
        program_semester_id: 'stage-1',
        semester_id: 'semester-1',
        name: 'Section B',
        code: 'CSE26B',
        capacity: 60,
      }),
    )
    expect(screen.getByRole('button', { name: 'View Section B, CSE 2026' }).closest('tr')).toHaveTextContent(
      'Unavailable',
    )
  })
  it('validates required fields, duplicate codes and whole-number capacity without losing entries', async () => {
    renderSections()
    const drawer = await openAdd()
    fireEvent.submit(drawer.getByRole('form'))
    expect(drawer.getByRole('alert')).toHaveTextContent('Enter a section name and code')
    fillSection('Section B', ' cse26a ')
    fireEvent.submit(drawer.getByRole('form'))
    expect(drawer.getByRole('alert')).toHaveTextContent('code already exists')
    fireEvent.change(drawer.getByRole('textbox', { name: 'Section Code' }), { target: { value: 'CSE26B' } })
    fireEvent.change(drawer.getByLabelText('Maximum Capacity (Optional)'), { target: { value: '2.5' } })
    fireEvent.submit(drawer.getByRole('form'))
    expect(drawer.getByRole('alert')).toHaveTextContent('nonnegative whole number')
    expect(api.createStructureRecord).not.toHaveBeenCalled()
  })
  it('edits status only after confirmation and retains immutable references', async () => {
    renderSections()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit Section A, CSE 2026' }))
    const drawer = within(screen.getByRole('dialog', { name: 'Edit Section' }))
    for (const field of ['Batch', 'Program Semester', 'Teaching Term'])
      expect(drawer.getByRole('combobox', { name: field })).toBeDisabled()
    expect(drawer.getByRole('textbox', { name: 'Section Code' })).toBeDisabled()
    fireEvent.click(drawer.getByRole('radio', { name: /^Inactive/ }))
    fireEvent.click(drawer.getByRole('button', { name: 'Save Changes' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Change' }))
    await waitFor(() =>
      expect(api.updateStructureRecord).toHaveBeenCalledWith(
        'token-1',
        'academic_sections',
        'section-1',
        expect.objectContaining({ is_active: false }),
      ),
    )
    expect(vi.mocked(api.updateStructureRecord).mock.calls[0][3]).not.toHaveProperty('admission_cohort_id')
  })
  it('confirms discard and keeps drafts after server errors', async () => {
    vi.mocked(api.createStructureRecord).mockRejectedValueOnce(new Error('Parent inactive'))
    renderSections()
    const drawer = await openAdd()
    fillSection()
    fireEvent.click(drawer.getByRole('button', { name: 'Create Section' }))
    expect(await drawer.findByRole('alert')).toHaveTextContent('Parent inactive')
    fireEvent.click(drawer.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('alertdialog', { name: 'Discard your changes?' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByRole('textbox', { name: 'Section Name' })).toHaveValue('Section B')
  })
})

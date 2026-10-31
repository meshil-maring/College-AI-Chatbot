import { api, renderStructure, structureCatalogue } from './Structure.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Curriculum creation and academic offerings', () => {
  it('creates a draft curriculum with its semester count', async () => {
    renderStructure()
    const trigger = screen.getByRole('button', { name: 'Add Curriculum' })
    await waitFor(() => expect(trigger).toBeEnabled())
    fireEvent.click(trigger)
    const drawer = within(screen.getByRole('dialog', { name: 'Add Curriculum' }))
    fireEvent.change(drawer.getByRole('combobox', { name: 'Program' }), { target: { value: 'program-1' } })
    fireEvent.change(drawer.getByRole('combobox', { name: 'Academic Year' }), { target: { value: 'year-1' } })
    fireEvent.change(drawer.getByRole('textbox', { name: 'Curriculum Name' }), { target: { value: 'New plan' } })
    fireEvent.change(drawer.getByRole('spinbutton', { name: 'Total Semesters' }), { target: { value: '4' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Create Curriculum' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'curriculum_versions',
      expect.objectContaining({ program_id: 'program-1', total_semesters: 4 }),
    )
  })
  it('limits offerings to a section’s assigned curriculum and program semester', async () => {
    structureCatalogue.records.academic_offerings = []
    renderStructure('offerings')
    const trigger = screen.getByRole('button', { name: 'Add Academic Offering' })
    await waitFor(() => expect(trigger).toBeEnabled())
    fireEvent.click(trigger)
    const drawer = within(screen.getByRole('dialog', { name: 'Add Academic Offering' }))
    fireEvent.change(drawer.getByRole('combobox', { name: 'Section' }), { target: { value: 'section-1' } })
    fireEvent.change(drawer.getByRole('combobox', { name: 'Curriculum Subject' }), { target: { value: 'mapping-1' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Create Academic Offering' }))
    await waitFor(() =>
      expect(api.createStructureRecord).toHaveBeenCalledWith(
        'token-1',
        'academic_offerings',
        expect.objectContaining({ academic_section_id: 'section-1', curriculum_subject_id: 'mapping-1' }),
      ),
    )
  })
  it('disables every write when the response is read-only', async () => {
    structureCatalogue.manageable = []
    renderStructure()
    await screen.findByRole('button', { name: 'View CSE Curriculum' })
    expect(screen.getByRole('button', { name: 'Add Curriculum' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Edit CSE Curriculum' })).toBeDisabled()
    expect(api.createStructureRecord).not.toHaveBeenCalled()
  })
})

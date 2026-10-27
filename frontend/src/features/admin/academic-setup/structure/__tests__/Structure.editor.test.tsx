import { api, renderStructure, structureCatalogue } from './Structure.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Program progression and academic offerings', () => {
  it('creates progression semesters independently of dated teaching terms', async () => {
    renderStructure()
    const trigger = screen.getByRole('button', { name: 'Add Program Semester' })
    await waitFor(() => expect(trigger).toBeEnabled())
    fireEvent.click(trigger)
    const drawer = within(screen.getByRole('dialog', { name: 'Add Program Semester' }))
    fireEvent.change(drawer.getByRole('combobox', { name: 'Program' }), { target: { value: 'program-1' } })
    fireEvent.change(drawer.getByRole('textbox', { name: 'Semester Name' }), { target: { value: 'Semester 2' } })
    fireEvent.change(drawer.getByRole('textbox', { name: 'Semester Code' }), { target: { value: 'S2' } })
    fireEvent.change(drawer.getByRole('spinbutton', { name: 'Semester Number' }), { target: { value: '2' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Create Program Semester' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'program_semesters',
      expect.objectContaining({ program_id: 'program-1', semester_number: 2 }),
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
    await screen.findByRole('button', { name: 'View Semester 1' })
    expect(screen.getByRole('button', { name: 'Add Program Semester' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Edit Semester 1' })).toBeDisabled()
    expect(api.createStructureRecord).not.toHaveBeenCalled()
  })
})

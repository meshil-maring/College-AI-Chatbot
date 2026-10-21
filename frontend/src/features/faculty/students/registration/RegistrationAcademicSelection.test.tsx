import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RegistrationAcademicSelection, { registrationClasses } from './RegistrationAcademicSelection.tsx'

const assignment = { assignment_id: 'a1', assigned_at: '', can_manage: true, section_id: 'section-1', semester_id: 's1', academic_year_id: 'y1', section: {
  section_id: 'section-1', name: 'Section A', code: 'A', program_id: 'p1',
  program: { program_id: 'p1', name: 'Computer Science', degree_type: 'B.Tech' }, course: { name: 'Data Mining', code: 'CS501' },
} }
const batches = [{ batch_id: 'batch-1', program_id: 'p1', start_year: 2026, end_year: 2030, is_active: true }]

describe('registration academic placement', () => {
  it('shows degree, branch, class section and admission batch without exposing subjects', () => {
    render(<RegistrationAcademicSelection assignments={[assignment]} sectionId="section-1" batch="batch-1" batches={batches} onBatch={vi.fn()} onSectionChange={vi.fn()} disabled={false} />)
    expect(screen.getByRole('combobox', { name: 'Course' })).toHaveDisplayValue('B.Tech')
    expect(screen.getByRole('combobox', { name: 'Branch' })).toHaveDisplayValue('Computer Science')
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toHaveDisplayValue('A')
    expect(screen.getByRole('combobox', { name: 'Batch' })).toHaveDisplayValue('2026–2030')
    expect(screen.queryByText(/Data Mining|CS501/)).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: /subject/i })).not.toBeInTheDocument()
  })

  it('deduplicates sibling subjects into one class and keeps degree and branch choices dependent', () => {
    const sibling = { ...assignment, section_id: 'section-2', section: { ...assignment.section, section_id: 'section-2', course: { name: 'Algorithms', code: 'CS502' } } }
    const other = { ...assignment, section_id: 'section-3', section: { ...assignment.section, section_id: 'section-3', program_id: 'p2', program: { program_id: 'p2', name: 'Commerce', degree_type: 'B.Com' } } }
    const readOnly = { ...assignment, section_id: 'read-only', can_manage: false }
    const onSectionChange = vi.fn()
    const classes = registrationClasses([assignment, sibling, other, readOnly])
    expect(classes).toHaveLength(2)
    expect(classes[0].ids).toEqual(['section-1', 'section-2'])
    render(<RegistrationAcademicSelection assignments={[assignment, sibling, other, readOnly]} sectionId="section-2" batch="" batches={batches} onBatch={vi.fn()} onSectionChange={onSectionChange} disabled={false} />)
    expect(within(screen.getByRole('combobox', { name: 'Section', exact: true })).getAllByRole('option')).toHaveLength(1)
    expect(within(screen.getByRole('combobox', { name: 'Branch' })).queryByRole('option', { name: 'Commerce' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Course' }), { target: { value: 'B.Com' } })
    expect(onSectionChange).toHaveBeenCalledWith('section-3')
  })

  it('fails closed when program metadata is missing', () => {
    render(<RegistrationAcademicSelection assignments={[{ ...assignment, section: { ...assignment.section, program: undefined } }]} sectionId="section-1" batch="" batches={batches} onBatch={vi.fn()} onSectionChange={vi.fn()} disabled={false} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Course and branch details are unavailable')
  })

  it('offers active saved batches for the selected branch and points to setup when none exist', () => {
    const onBatch = vi.fn()
    const view = render(<RegistrationAcademicSelection assignments={[assignment]} sectionId="section-1" batch="" batches={[
      ...batches, { ...batches[0], batch_id: 'archived', start_year: 2024, end_year: 2028, is_active: false },
      { ...batches[0], batch_id: 'foreign-branch', program_id: 'p2', start_year: 2025, end_year: 2029 },
    ]} onBatch={onBatch} onSectionChange={vi.fn()} disabled={false} />)
    const selector = screen.getByRole('combobox', { name: 'Batch' })
    expect(within(selector).getAllByRole('option')).toHaveLength(2)
    fireEvent.change(selector, { target: { value: 'batch-1' } })
    expect(onBatch).toHaveBeenCalledWith('batch-1')
    view.rerender(<RegistrationAcademicSelection assignments={[assignment]} sectionId="section-1" batch="" batches={[]} onBatch={onBatch} onSectionChange={vi.fn()} disabled={false} />)
    expect(screen.getByRole('combobox', { name: 'Batch' })).toBeDisabled()
    expect(screen.getByText(/Academic Setup → Batches/)).toBeInTheDocument()
  })
})

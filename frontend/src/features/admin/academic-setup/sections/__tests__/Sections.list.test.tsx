import { api, section, structureCatalogue, renderSections } from './Sections.support.tsx'
import { fireEvent, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Stored section records', () => {
  it('reads saved records, paginates and keeps unknown enrollment totals distinct', async () => {
    structureCatalogue.records.academic_sections = Array.from({ length: 21 }, (_, index) => ({
      ...section,
      academic_section_id: `section-${index}`,
      name: `Section ${index + 1}`,
      code: `CSE26-${index + 1}`,
    }))
    renderSections()
    await screen.findByText('Showing 1 to 10 of 21 sections')
    expect(screen.getByRole('article', { name: 'Total Sections' })).toHaveTextContent('21')
    expect(screen.getByRole('article', { name: 'Total Students' })).toHaveTextContent('Enrollment data unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Page 3' }))
    expect(screen.getByText('Showing 21 to 21 of 21 sections')).toBeInTheDocument()
    expect(api.getAcademicStructure).toHaveBeenCalled()
    expect(screen.queryByText(/Design preview/)).not.toBeInTheDocument()
  })
  it('combines filters, resets pagination and sorts saved section codes', async () => {
    renderSections()
    await screen.findByRole('button', { name: 'View Section A, CSE 2026' })
    const filters = within(screen.getByRole('search', { name: 'Filter sections' }))
    fireEvent.change(filters.getByRole('searchbox'), { target: { value: ' CSE ' } })
    fireEvent.change(filters.getByLabelText('Batch'), { target: { value: 'cohort-1' } })
    fireEvent.change(filters.getByLabelText('Program'), { target: { value: 'program-1' } })
    fireEvent.change(filters.getByLabelText('Status'), { target: { value: 'inactive' } })
    expect(screen.getByRole('heading', { name: 'No sections found' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.click(screen.getByRole('button', { name: 'Code', exact: true }))
    expect(screen.getByRole('columnheader', { name: 'Code' })).toHaveAttribute('aria-sort', 'ascending')
    expect(screen.getByText('Showing 1 to 1 of 1 sections')).toBeInTheDocument()
  })
})

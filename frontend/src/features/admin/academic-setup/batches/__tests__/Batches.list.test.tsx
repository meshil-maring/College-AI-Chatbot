import { api, cohort, structureCatalogue, renderBatches } from './Batches.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Stored batches', () => {
  it('reads institution records, paginates and keeps enrollment totals unavailable', async () => {
    structureCatalogue.records.admission_cohorts = Array.from({ length: 21 }, (_, index) => ({
      ...cohort,
      admission_cohort_id: `cohort-${index}`,
      name: `Batch ${index + 1}`,
      code: `B${index + 1}`,
    }))
    renderBatches()
    await screen.findByText('Showing 1 to 10 of 21 batches')
    expect(screen.getByRole('article', { name: 'Total Batches' })).toHaveTextContent('21')
    expect(screen.getByRole('article', { name: 'Total Students' })).toHaveTextContent('Enrollment data unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Page 3' }))
    expect(screen.getByText('Showing 21 to 21 of 21 batches')).toBeInTheDocument()
    expect(api.getAcademicStructure).toHaveBeenCalled()
    expect(screen.queryByText(/Design preview/)).not.toBeInTheDocument()
  })
  it('combines search, program, year and status filters', async () => {
    renderBatches()
    await screen.findByRole('button', { name: 'View CSE 2026' })
    const filters = within(screen.getByRole('search', { name: 'Filter batches' }))
    fireEvent.change(filters.getByRole('searchbox'), { target: { value: ' CSE ' } })
    fireEvent.change(filters.getByLabelText('Program'), { target: { value: 'program-1' } })
    fireEvent.change(filters.getByLabelText('Academic Year'), { target: { value: 'year-1' } })
    fireEvent.change(filters.getByLabelText('Status'), { target: { value: 'active' } })
    expect(screen.getByText('Showing 1 to 1 of 1 batches')).toBeInTheDocument()
    fireEvent.change(filters.getByLabelText('Status'), { target: { value: 'inactive' } })
    expect(screen.getByRole('heading', { name: 'No batches found' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'View CSE 2026' })).toBeInTheDocument())
  })
})

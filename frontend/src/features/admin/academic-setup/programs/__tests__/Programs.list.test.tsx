import { api, catalogue, department, program, renderPrograms } from './Programs.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Programs management list', () => {
  it('uses scoped totals and never exposes foreign programs or department names', async () => {
    catalogue.records.programs = [
      program,
      { ...program, program_id: 'foreign', name: 'Foreign Program', institution_id: 'foreign' },
    ]
    catalogue.records.departments!.push({
      ...department,
      department_id: 'foreign',
      name: 'Foreign Department',
      institution_id: 'foreign',
    })
    renderPrograms()
    expect(await screen.findByRole('row', { name: /B.Tech CSE/ })).toBeInTheDocument()
    const summary = screen.getByRole('region', { name: 'Program summary' })
    expect(within(summary).getByText('Total Programs').parentElement).toHaveTextContent('1')
    expect(within(summary).getByText('Departments').parentElement).toHaveTextContent('1')
    expect(screen.queryByText('Foreign Program')).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Foreign Department' })).not.toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('paginates eight records and resets the page when filters change', async () => {
    catalogue.records.programs = Array.from({ length: 12 }, (_, i) => ({
      ...program,
      program_id: `p-${i}`,
      name: `Program ${i + 1}`,
      code: `P${i + 1}`,
    }))
    renderPrograms()
    await screen.findByText('Showing 1 to 8 of 12 programs')
    fireEvent.click(screen.getByRole('button', { name: 'Next program page' }))
    expect(screen.getByText('Showing 9 to 12 of 12 programs')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search programs' }), { target: { value: 'P12' } })
    expect(screen.getByText('Showing 1 to 1 of 1 programs')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous program page' })).toBeDisabled()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search programs' }), { target: { value: 'Missing' } })
    expect(screen.getByRole('heading', { name: 'No programs match your filters' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByText('Showing 1 to 8 of 12 programs')).toBeInTheDocument()
  })

  it('combines department, degree and status filters and sorts numeric credits', async () => {
    catalogue.records.departments!.push({ ...department, department_id: 'math', name: 'Mathematics', code: 'MATH' })
    catalogue.records.programs = [
      program,
      {
        ...program,
        program_id: 'math',
        name: 'Mathematics',
        department_id: 'math',
        degree_type: 'B.Sc',
        is_active: false,
        total_credits: 9,
      },
      { ...program, program_id: 'applied', name: 'Applied Mathematics', total_credits: 100 },
    ]
    renderPrograms()
    await screen.findByRole('button', { name: 'View Mathematics' })
    const filters = screen.getByRole('search', { name: 'Filter programs' })
    fireEvent.change(within(filters).getByRole('combobox', { name: 'Department' }), { target: { value: 'math' } })
    fireEvent.change(within(filters).getByRole('combobox', { name: 'Degree Type' }), { target: { value: 'B.Sc' } })
    fireEvent.change(within(filters).getByRole('combobox', { name: 'Status' }), { target: { value: 'inactive' } })
    expect(screen.getByText('Showing 1 to 1 of 1 programs')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'View B.Tech CSE' })).not.toBeInTheDocument()
    fireEvent.change(within(filters).getByRole('combobox', { name: 'Department' }), { target: { value: '' } })
    fireEvent.change(within(filters).getByRole('combobox', { name: 'Degree Type' }), { target: { value: '' } })
    fireEvent.change(within(filters).getByRole('combobox', { name: 'Status' }), { target: { value: 'all' } })
    fireEvent.click(screen.getByRole('button', { name: 'Credits', exact: true }))
    const rows = within(screen.getByRole('region', { name: 'Program records' })).getAllByRole('row')
    expect(rows[1]).toHaveTextContent('Mathematics')
    expect(rows[2]).toHaveTextContent('Applied Mathematics')
    expect(rows[3]).toHaveTextContent('B.Tech CSE')
  })

  it('navigates from the sidebar and overview shortcut into the dedicated page', async () => {
    renderPrograms('overview')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Program', exact: true })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Add Program', exact: true }))
    expect(await screen.findByRole('dialog', { name: 'Add Program' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Programs', level: 1 })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })
})

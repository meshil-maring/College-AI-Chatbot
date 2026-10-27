import { api, catalogue, department, program, renderDepartments } from './Departments.support.tsx'
import { act, fireEvent, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AcademicCatalogue } from '../../../../../types/academicSetup.ts'

describe('Departments list', () => {
  it('shows only institution records and counts only readable associated programs', async () => {
    catalogue.records.departments!.push({
      ...department,
      department_id: 'foreign',
      name: 'Foreign Department',
      institution_id: 'foreign',
    })
    catalogue.records.programs = [program, { ...program, program_id: 'foreign-program', institution_id: 'foreign' }]
    renderDepartments()
    const row = await screen.findByRole('row', { name: /Computer Science and Engineering/ })
    expect(within(row).getByText('1')).toBeInTheDocument()
    const summary = screen.getByRole('region', { name: 'Department summary' })
    expect(within(summary).getAllByText('1')).toHaveLength(2)
    expect(within(summary).getByText('0')).toBeInTheDocument()
    expect(screen.queryByText('Foreign Department')).not.toBeInTheDocument()
    fireEvent.click(within(row).getByRole('button', { name: /View/ }))
    const drawer = screen.getByRole('dialog', { name: 'Department details' })
    expect(within(drawer).getByText(program.name)).toBeInTheDocument()
    expect(within(drawer).getAllByRole('listitem')).toHaveLength(1)
    expect(screen.queryByLabelText(/Campus|Head of Department/)).not.toBeInTheDocument()
  })

  it('distinguishes unavailable program data from a confirmed empty program list', async () => {
    delete catalogue.records.programs
    renderDepartments()
    const row = await screen.findByRole('row', { name: /Computer Science and Engineering/ })
    expect(within(row).getByText('Unavailable')).toBeInTheDocument()
    fireEvent.click(within(row).getByRole('button', { name: /View/ }))
    expect(screen.getByText('Program data is not connected.')).toBeInTheDocument()
    expect(screen.queryByText('No associated programs.')).not.toBeInTheDocument()
  })

  it('reserves loading rows and shows zero only after a successful empty response', async () => {
    let resolve!: (value: AcademicCatalogue) => void
    vi.mocked(api.getAcademicSetup).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    renderDepartments()
    expect(screen.getByRole('region', { name: 'Department summary' })).toHaveAttribute('aria-busy', 'true')
    expect(screen.queryByText('No departments yet')).not.toBeInTheDocument()
    await act(async () => resolve({ ...catalogue, records: { departments: [] } }))
    expect(await screen.findByText('No departments yet')).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Department summary' })).getAllByText('0')).toHaveLength(3)
  })

  it('searches, filters, sorts and paginates without changing institution totals', async () => {
    catalogue.records.departments!.push(
      ...Array.from({ length: 5 }, (_, i) => ({
        ...department,
        department_id: `department-${i + 2}`,
        name: `Department ${String.fromCharCode(66 + i)}`,
        code: `X${i}`,
        is_active: i !== 4,
      })),
    )
    renderDepartments()
    await screen.findByText('Showing 1 to 5 of 6 departments')
    fireEvent.click(screen.getByRole('button', { name: 'Next department page' }))
    expect(await screen.findByText('Showing 6 to 6 of 6 departments')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Status' }), { target: { value: 'inactive' } })
    expect(screen.getByText('Showing 1 to 1 of 1 departments')).toBeInTheDocument()
    expect(screen.getByText('Department F')).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Department summary' })).getByText('6')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Status' }), { target: { value: 'all' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Sort by' }), { target: { value: 'code-desc' } })
    expect(screen.getAllByRole('row')[1]).toHaveTextContent('Department F')
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'aerospace' } })
    expect(screen.getByText('No departments match your filters')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByRole('searchbox')).toHaveValue('')
    expect(screen.getByText('Showing 1 to 5 of 6 departments')).toBeInTheDocument()
  })

  it('opens the Departments section from the existing sidebar', async () => {
    renderDepartments('overview')
    fireEvent.click(
      within(screen.getByRole('navigation', { name: 'Academic Setup navigation' })).getByRole('button', {
        name: 'Departments',
        exact: true,
      }),
    )
    expect(screen.getByRole('heading', { name: 'Departments', level: 1 })).toBeInTheDocument()
    expect(await screen.findByRole('row', { name: /Computer Science and Engineering/ })).toBeInTheDocument()
    expect(screen.queryByText('Existing catalogue available')).not.toBeInTheDocument()
  })
})

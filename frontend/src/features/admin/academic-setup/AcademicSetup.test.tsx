import './__tests__/AcademicSetup.support.ts'
import { catalogue, department, program, year } from './__tests__/AcademicSetup.support.ts'
import * as api from '../../../services/admin/academics.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AcademicSetup from './AcademicSetup.tsx'

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label, { exact: true }), { target: { value } })
}

describe('Academic Setup Stage 1', () => {
  it('creates CSE, its degree program and the 2026–2027 academic year', async () => {
    catalogue.records.departments = []
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Add department' }))
    fill('Name', department.name)
    fill('Code', department.code)
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('heading', { name: department.name })
    fireEvent.click(screen.getByRole('button', { name: 'Programs' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add degree program' }))
    fill('Name', program.name)
    fill('Code', program.code)
    fireEvent.change(screen.getByRole('combobox', { name: /Department/ }), { target: { value: 'new-departments' } })
    fill('Degree type', 'B.Tech')
    fill('Duration (years)', '4')
    fill('Total credits (optional)', '160')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('heading', { name: program.name })
    expect(api.createAcademicRecord).toHaveBeenCalledWith(
      'token-1',
      'programs',
      expect.objectContaining({
        department_id: 'new-departments',
        degree_type: 'B.Tech',
        duration_years: 4,
        total_credits: 160,
      }),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Academic years' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add academic year' }))
    fill('Name', year.name)
    fill('Code', year.code)
    fill('Start date', year.start_date)
    fill('End date', year.end_date)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Current academic year' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('heading', { name: year.name })
    expect(api.createAcademicRecord).toHaveBeenCalledWith(
      'token-1',
      'academic_years',
      expect.objectContaining({
        start_date: '2026-07-01',
        end_date: '2027-06-30',
        is_current: true,
      }),
    )
    expect(
      within(screen.getByRole('navigation', { name: 'Academic Setup pages' })).getAllByRole('button'),
    ).toHaveLength(3)
    expect(screen.queryByRole('button', { name: /Subjects|Semesters|Sections/ })).not.toBeInTheDocument()
  })

  it('edits degree metadata without changing its department and retains an inactive parent', async () => {
    catalogue.records.departments![0].is_active = false
    catalogue.records.programs = [structuredClone(program)]
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Programs' }))
    fireEvent.click(screen.getByRole('button', { name: `Edit ${program.name}` }))
    const parent = screen.getByRole('combobox', { name: /Department/ })
    expect(parent).toBeDisabled()
    expect(parent).toHaveDisplayValue(`${department.name} (${department.code}) (inactive)`)
    fill('Name', 'B.Tech Computer Science Engineering')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.updateAcademicRecord).toHaveBeenCalled())
    const payload = vi.mocked(api.updateAcademicRecord).mock.calls[0][3]
    expect(payload).not.toHaveProperty('department_id')
    expect(payload).toHaveProperty('name', 'B.Tech Computer Science Engineering')
  })

  it('requires an active department before creating a degree program', async () => {
    catalogue.records.departments![0].is_active = false
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Programs' }))
    expect(screen.getByRole('button', { name: 'Add degree program' })).toBeDisabled()
    expect(screen.getByText(/An active department must be available/)).toBeInTheDocument()
  })

  it('deactivates the current year safely and permits reactivation', async () => {
    catalogue.records.academic_years = [structuredClone(year)]
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Academic years' }))
    fireEvent.click(screen.getByRole('button', { name: `Deactivate ${year.name}` }))
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toHaveTextContent('clear its current designation')
    fireEvent.click(screen.getByRole('button', { name: 'Confirm deactivation' }))
    expect(await screen.findByRole('button', { name: `Activate ${year.name}` })).toBeEnabled()
    expect(api.updateAcademicRecord).toHaveBeenCalledWith('token-1', 'academic_years', year.academic_year_id, {
      is_active: false,
      is_current: false,
    })
    fireEvent.click(screen.getByRole('button', { name: `Activate ${year.name}` }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm activation' }))
    await screen.findByRole('button', { name: `Deactivate ${year.name}` })
    expect(api.updateAcademicRecord).toHaveBeenLastCalledWith('token-1', 'academic_years', year.academic_year_id, {
      is_active: true,
    })
  })

  it('shows duplicate/tenant/child-dependency failures without claiming success', async () => {
    vi.mocked(api.updateAcademicRecord).mockRejectedValue(
      new Error('Deactivate active programs before their department.'),
    )
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: `Deactivate ${department.name}` }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm deactivation' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Deactivate active programs')
    expect(screen.queryByText('Saved successfully.')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Deactivate ${department.name}` })).toBeEnabled()
    vi.mocked(api.createAcademicRecord).mockRejectedValue(new Error('This code already exists.'))
    fireEvent.click(screen.getByRole('button', { name: 'Add department' }))
    fill('Name', department.name)
    fill('Code', department.code)
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This code already exists.')
    expect(screen.getByRole('form', { name: 'New department' })).toBeInTheDocument()
  })

  it('validates academic-year date order before sending a request', async () => {
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: 'Academic years' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add academic year' }))
    fill('Name', year.name)
    fill('Code', year.code)
    fill('Start date', '2027-06-30')
    fill('End date', '2026-07-01')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('End date must be after')
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })
  it('cancels a sensitive transition without changing a record', async () => {
    render(<AcademicSetup />)
    fireEvent.click(await screen.findByRole('button', { name: `Deactivate ${department.name}` }))
    expect(screen.getByRole('dialog')).toHaveTextContent(department.name)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: `Deactivate ${department.name}` })).toBeEnabled()
  })
})

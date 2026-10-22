import './__tests__/AcademicSetup.support.tsx'
import { fixture, loaded, tab } from './__tests__/AcademicSetup.support.tsx'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'
import AcademicSetup from './AcademicSetup.tsx'

describe('Academic setup directory', () => {
  it('selects departments and shows their actual related degree programs', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    const detail = screen.getByRole('complementary', { name: 'Department details' })
    expect(within(detail).getByText('Science degree')).toBeInTheDocument()
    expect(within(detail).queryByText('Unavailable')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Archived', exact: true }))
    expect(within(detail).getByRole('heading', { name: 'OLD' })).toBeInTheDocument()
    expect(within(detail).queryByText('Science degree')).not.toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('combines search and availability filters and resets them when changing workflows', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.change(screen.getByRole('textbox', { name: 'Search departments' }), { target: { value: 'old' } })
    expect(screen.getByRole('button', { name: 'Archived', exact: true })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Science', exact: true })).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by status' }), { target: { value: 'active' } })
    expect(screen.getByText('No records match your filters.')).toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: 'Department details' })).not.toBeInTheDocument()
    tab('Programs')
    expect(screen.getByRole('textbox', { name: 'Search degree programs' })).toHaveValue('')
    expect(screen.getByRole('combobox', { name: 'Filter by status' })).toHaveValue('all')
    expect(screen.getByRole('button', { name: 'Science degree', exact: true })).toBeInTheDocument()
  })

  it('paginates records and updates the detail selection with each page', async () => {
    const data = fixture()
    data.records.departments = Array.from({ length: 8 }, (_, index) => ({
      department_id: `d${index}`,
      name: `Department ${index}`,
      code: `D${index}`,
      is_active: true,
    }))
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    expect(screen.getByText('Showing 1 to 6 of 8 departments')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Department 2', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Showing 7 to 8 of 8 departments')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
    expect(
      within(screen.getByRole('complementary', { name: 'Department details' })).getByRole('heading', { name: 'D6' }),
    ).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Search departments' }), { target: { value: 'D7' } })
    expect(screen.getByText('Showing 1 to 1 of 1 departments')).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('filters dated teaching terms by academic year within Calendar', async () => {
    const data = fixture()
    data.records.academic_years![0].is_current = true
    data.records.sections = [
      { section_id: 'section', course_offering_id: 'o', name: 'Section A', code: 'A', is_active: true },
    ]
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    expect(screen.getByRole('button', { name: 'Archived', exact: true })).toBeInTheDocument()
    tab('Semesters')
    fireEvent.change(screen.getByRole('combobox', { name: 'Academic year filter' }), { target: { value: 'y' } })
    expect(screen.getByRole('button', { name: 'Semester 1', exact: true })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Foreign term', exact: true })).not.toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('disables navigation and year changes while a record is unsaved', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add Department' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Unsaved' } })
    expect(screen.getByRole('combobox', { name: 'Record type' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Science', exact: true })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Refresh academic setup' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('combobox', { name: 'Record type' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Science', exact: true })).toBeEnabled()
  })
})

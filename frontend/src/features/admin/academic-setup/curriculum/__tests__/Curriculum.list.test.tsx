import { api, catalogue, course, link, program, semester, renderCurriculum, loaded } from './Curriculum.support.tsx'
import { fireEvent, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Curriculum layout and existing program mappings', () => {
  it('displays scoped records without inventing curriculum versions or lifecycle totals', async () => {
    catalogue.records.programs!.push({
      ...program,
      program_id: 'foreign',
      name: 'Foreign Program',
      institution_id: 'foreign',
    })
    catalogue.records.courses!.push({ ...course, name: 'Foreign Subject', institution_id: 'foreign' })
    catalogue.records.program_courses!.push({
      ...link,
      program_course_id: 'foreign',
      course_type: 'project',
      institution_id: 'foreign',
    })
    catalogue.records.semesters!.push({ ...semester, name: 'Foreign Term', institution_id: 'foreign' })
    renderCurriculum()
    await loaded()
    expect(screen.getByRole('heading', { name: 'Curriculum', level: 1 })).toBeInTheDocument()
    const summary = within(screen.getByRole('region', { name: 'Curriculum summary' }))
    expect(summary.getByText('Total Curricula').parentElement).toHaveTextContent('—')
    expect(summary.getByText('Programs').parentElement).toHaveTextContent('1')
    const row = screen.getByRole('row', { name: /Data Mining/ })
    expect(row).toHaveTextContent('Core')
    expect(row).not.toHaveTextContent('Project')
    expect(screen.queryByText('Foreign Program')).not.toBeInTheDocument()
    expect(screen.queryByText('Foreign Subject')).not.toBeInTheDocument()
    expect(screen.queryByText('Foreign Term')).not.toBeInTheDocument()
    expect(screen.getByText('Unversioned', { selector: '.curriculum-version-tag' })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('paginates seven programs and combines search, status and program filters', async () => {
    catalogue.records.programs = Array.from({ length: 10 }, (_, index) => ({
      ...program,
      program_id: `program-${index}`,
      name: `Program ${index + 1}`,
      code: `P${index + 1}`,
      is_active: index !== 9,
    }))
    renderCurriculum()
    await loaded()
    expect(screen.getByText('Showing 1 to 7 of 10 programs')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next curriculum page' }))
    expect(screen.getByText('Showing 8 to 10 of 10 programs')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search curriculum programs' }), {
      target: { value: 'P10' },
    })
    expect(screen.getByText('Showing 1 to 1 of 1 programs')).toBeInTheDocument()
    const filters = within(screen.getByRole('search', { name: 'Filter curriculum programs' }))
    fireEvent.change(filters.getByRole('combobox', { name: 'Status' }), { target: { value: 'active' } })
    expect(screen.getByRole('heading', { name: 'No programs match your filters' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.change(filters.getByRole('combobox', { name: 'Program' }), { target: { value: 'program-4' } })
    expect(screen.getByText('Showing 1 to 1 of 1 programs')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Selected program curriculum' })).toHaveTextContent('Program 5')
  })

  it('shows dated semester groups, all-semester mappings and unknown credits accurately', async () => {
    catalogue.records.program_courses!.push({ ...link, program_course_id: 'unassigned', course_type: 'elective' })
    catalogue.records.courses![0].credits = null
    renderCurriculum()
    await loaded()
    expect(screen.getByText('Semester 1', { selector: 'summary strong' })).toBeInTheDocument()
    expect(screen.getByText('Autumn (AUT)')).toBeInTheDocument()
    expect(screen.getByText('All semesters', { selector: 'summary strong' })).toBeInTheDocument()
    expect(screen.getAllByText('Credits unavailable', { exact: false }).length).toBeGreaterThan(0)
    expect(screen.getByText(/Existing dated academic terms/)).toBeInTheDocument()
  })

  it('switches top-level and detail tabs with keyboard navigation and retains existing mapping details', async () => {
    renderCurriculum()
    await loaded()
    const tab = screen.getByRole('tab', { name: 'Curriculum List' })
    tab.focus()
    fireEvent.keyDown(tab, { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Curriculum Structure' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Curriculum Structure' })).toHaveFocus()
    fireEvent.click(screen.getByRole('tab', { name: 'Curriculum List' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Overview', exact: true }))
    expect(screen.getByRole('tabpanel', { name: 'Overview', exact: true })).toHaveTextContent(program.degree_type)
    fireEvent.click(screen.getByRole('tab', { name: 'Program Outcomes' }))
    expect(screen.getByRole('heading', { name: 'Program outcomes are not connected' })).toBeInTheDocument()
  })

  it('opens the mapping view directly from the curriculum-subjects navigation', async () => {
    renderCurriculum('curriculum-subjects')
    await loaded()
    expect(screen.getByRole('tab', { name: 'Subject Mapping' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('row', { name: /Data Mining/ })).toBeInTheDocument()
  })
})

import { api, catalogue, semester, year, renderCalendar } from './Calendar.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('Academic calendar views', () => {
  it('shows tenant counts, expands the current year and displays its dated semesters', async () => {
    catalogue.records.academic_years!.push({ ...year, academic_year_id: 'foreign', institution_id: 'foreign' })
    catalogue.records.semesters!.push({ ...semester, semester_id: 'foreign', institution_id: 'foreign' })
    renderCalendar()
    await screen.findByRole('article', { name: year.name }, { timeout: 5000 })
    const summary = screen.getByRole('region', { name: 'Academic calendar summary' })
    expect(summary).toHaveTextContent('Total Academic Years2')
    expect(summary).toHaveTextContent('Total Semesters2')
    const card = within(screen.getByRole('article', { name: year.name }))
    expect(card.getByRole('button', { expanded: true })).toHaveTextContent(year.name)
    expect(card.getByRole('table', { name: 'Semesters' })).toHaveTextContent('Semester 1')
    fireEvent.click(card.getByRole('button', { expanded: true }))
    expect(card.queryByRole('table')).not.toBeInTheDocument()
  })

  it('combines search and status filters and sorts years', async () => {
    renderCalendar()
    await screen.findByRole('article', { name: year.name })
    fireEvent.change(screen.getByRole('combobox', { name: 'Status' }), { target: { value: 'completed' } })
    expect(screen.queryByRole('article', { name: year.name })).not.toBeInTheDocument()
    expect(screen.getByRole('article', { name: '2024 - 2025' })).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'AY2026' } })
    expect(screen.getByRole('heading', { name: 'No matching records' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Sort by' }), { target: { value: 'oldest' } })
    expect(within(screen.getByRole('tabpanel')).getAllByRole('article')[0]).toHaveAccessibleName('2024 - 2025')
  })

  it('paginates years and resets the page after filtering', async () => {
    for (let i = 0; i < 7; i++)
      catalogue.records.academic_years!.push({
        ...year,
        academic_year_id: `old-${i}`,
        name: `${2010 + i}`,
        code: `AY${2010 + i}`,
        start_date: `${2010 + i}-08-01`,
        end_date: `${2011 + i}-07-31`,
        is_current: false,
      })
    renderCalendar()
    await screen.findByRole('article', { name: year.name })
    expect(within(screen.getByRole('tabpanel')).getAllByRole('article')).toHaveLength(6)
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Showing 7 to 9 of 9 academic years')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: year.code } })
    expect(screen.getByText('Showing 1 to 1 of 1 academic years')).toBeInTheDocument()
  })

  it('supports keyboard tabs and derives important dates and timeline from real records', async () => {
    renderCalendar()
    await screen.findByRole('article', { name: year.name })
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Academic Years' }), { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Semesters' })).toHaveFocus()
    expect(screen.getByRole('tab', { name: 'Semesters' })).toHaveAttribute('aria-selected', 'true')
    expect(within(screen.getByRole('tabpanel')).getByRole('row', { name: /Semester 2/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Important Dates' }))
    expect(screen.getByText('Semester 1 begins')).toBeInTheDocument()
    expect(screen.getByText('Semester 2 ends')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Overview Timeline' }))
    fireEvent.click(screen.getByRole('button', { name: 'Semester 1', exact: true }))
    expect(screen.getByRole('dialog', { name: 'Semester details' })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('opens the year creation shortcut and semester destination in the new calendar', async () => {
    renderCalendar('overview')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Configure Academic Year' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Configure Academic Year' }))
    expect(await screen.findByRole('dialog', { name: 'Add Academic Year' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(
      within(screen.getByRole('navigation', { name: 'Academic Setup navigation' })).getByRole('button', {
        name: 'Academic Terms',
        exact: true,
      }),
    )
    expect(screen.getByRole('tab', { name: 'Semesters' })).toHaveAttribute('aria-selected', 'true')
  })
})

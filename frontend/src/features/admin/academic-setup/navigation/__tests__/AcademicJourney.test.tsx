import '../../__tests__/AcademicSetup.support.ts'
import { structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
import { populateStructure } from '../../__tests__/academicStructureFixtures.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../../../../services/academics/semesterRegistration.ts'
import * as structureApi from '../../../../../services/admin/academicStructure.ts'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

vi.mock('../../../../../services/academics/semesterRegistration.ts')

beforeEach(() => {
  populateStructure()
  vi.mocked(api.getRegistrationCatalogue).mockResolvedValue({
    institution_id: 'institution-1',
    groups: [],
    students: [],
    assignments: [],
    can_assign: true,
    can_manage_choices: true,
  })
})

function Workspace({ initial = 'overview' }: { initial?: AcademicPage }) {
  const [page, setPage] = useState(initial)
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}

it.each(['curriculum-options', 'program-semesters'] as const)(
  'opens old %s destinations in the combined semester screen',
  async (initial) => {
    render(<Workspace initial={initial} />)
    const sidebar = within(screen.getByRole('navigation', { name: 'Academic Setup navigation' }))
    await screen.findByRole('heading', { name: 'Subjects by semester', level: 1 })
    expect(screen.getByRole('complementary', { name: 'Key distinction' })).toHaveTextContent(
      'Curriculum semesters are about study progression',
    )
    expect(sidebar.queryByRole('button', { name: 'Subject Options', exact: true })).not.toBeInTheDocument()
    expect(sidebar.queryByRole('button', { name: 'Program Semesters', exact: true })).not.toBeInTheDocument()
    expect(sidebar.getByRole('button', { name: 'Subjects by semester', exact: true })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.queryByRole('tab', { name: 'Subject Options' })).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Subjects by semester' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Back to curriculum list', exact: true }))
    expect(screen.getByRole('tab', { name: 'Curriculum List' })).toHaveAttribute('aria-selected', 'true')
    expect(sidebar.getByRole('button', { name: 'Curriculum Versions', exact: true })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(structureApi.updateStructureRecord).not.toHaveBeenCalled()
  },
)

it('guides a published curriculum through batches, sections, offerings and student enrollment', async () => {
  render(<Workspace initial="curriculum-versions" />)
  fireEvent.click(screen.getByRole('button', { name: /Curriculum already published/ }))
  await screen.findByRole('heading', { name: 'Batches', level: 1 })
  expect(screen.getByRole('complementary', { name: 'Key distinction' })).toHaveTextContent(
    'Batch and section are different',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Set up sections (optional)', exact: true }))
  await screen.findByRole('heading', { name: 'Sections', level: 1 })
  expect(screen.getByRole('complementary', { name: 'Key distinction' })).toHaveTextContent('A section is a class group')
  fireEvent.click(screen.getByRole('button', { name: 'Offer section subjects', exact: true }))
  await screen.findByRole('heading', { name: 'Academic Offerings', level: 1 })
  fireEvent.click(screen.getByRole('button', { name: 'Assign students to sections', exact: true }))
  await screen.findByRole('heading', { name: 'Student Enrollment', level: 1 })
  expect(screen.getByRole('region', { name: 'Academic setup guide' })).toHaveTextContent(
    'Semester Registration in their student portal',
  )
  expect(api.assignStudentSemester).not.toHaveBeenCalled()
  expect(structureApi.createStructureRecord).not.toHaveBeenCalled()
})

it('explains dated teaching terms separately from curriculum progression', async () => {
  render(<Workspace initial="terms" />)
  await screen.findByRole('heading', { name: 'Academic Calendar', level: 1 })
  expect(screen.getByRole('complementary', { name: 'Key distinction' })).toHaveTextContent(
    'Calendar terms are about when',
  )
  expect(screen.getByRole('complementary', { name: 'Key distinction' })).toHaveTextContent(
    'Curriculum semesters are numbered stages',
  )
})

it('shows descriptions for each setup step on the overview', () => {
  render(<Workspace />)
  const guide = screen.getByRole('region', { name: 'Academic setup guide' })
  expect(within(guide).getByText(/Create programs, set dated teaching periods/)).toBeInTheDocument()
  expect(within(guide).getByText(/Create an intake batch and assign its published curriculum/)).toBeInTheDocument()
  expect(within(guide).getByText(/Create the class groups you need/)).toBeInTheDocument()
})

it('keeps curriculum tabs and sidebar selection synchronized', async () => {
  render(<Workspace initial="curriculum-versions" />)
  fireEvent.click(screen.getByRole('tab', { name: 'Subjects by semester' }))
  const sidebar = within(screen.getByRole('navigation', { name: 'Academic Setup navigation' }))
  expect(sidebar.getByRole('button', { name: 'Subjects by semester', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  )
  fireEvent.click(screen.getByRole('tab', { name: 'Version History' }))
  expect(sidebar.getByRole('button', { name: 'Version History', exact: true })).toHaveAttribute('aria-current', 'page')
  expect(screen.getByRole('region', { name: 'Published curriculum history' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Existing Program Mappings' }))
  expect(sidebar.getByRole('button', { name: 'Existing Program Mappings', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  )
})

it('keeps keyboard focus on the selected curriculum tab after arrow navigation', () => {
  render(<Workspace initial="curriculum-versions" />)
  const listTab = screen.getByRole('tab', { name: 'Curriculum List' })
  listTab.focus()
  fireEvent.keyDown(listTab, { key: 'ArrowRight' })
  const mappingTab = screen.getByRole('tab', { name: 'Subjects by semester' })
  expect(mappingTab).toHaveAttribute('aria-selected', 'true')
  expect(mappingTab).toHaveAttribute('tabindex', '0')
  expect(mappingTab).toHaveFocus()
})

it('keeps search focused when typing opens the overview results', () => {
  function SearchableWorkspace() {
    const [page, setPage] = useState<AcademicPage>('curriculum-options')
    return (
      <>
        <input type="search" aria-label="Search setup" onChange={() => setPage('overview')} />
        <AcademicWorkspace page={page} search="option" onNavigate={setPage} onClearSearch={vi.fn()} />
      </>
    )
  }
  render(<SearchableWorkspace />)
  const search = screen.getByRole('searchbox', { name: 'Search setup' })
  search.focus()
  fireEvent.change(search, { target: { value: 'option' } })
  expect(search).toHaveFocus()
  expect(screen.getByRole('heading', { name: 'Academic Setup', level: 1 })).toBeInTheDocument()
})

it('keeps calendar tabs, filters and sidebar selection synchronized with keyboard navigation', async () => {
  render(<Workspace initial="years" />)
  await screen.findByRole('heading', { name: 'Academic Calendar', level: 1 })
  const search = screen.getByRole('searchbox', { name: 'Search academic calendar' })
  fireEvent.change(search, { target: { value: '2026' } })
  const yearTab = screen.getByRole('tab', { name: 'Academic Years' })
  yearTab.focus()
  fireEvent.keyDown(yearTab, { key: 'ArrowRight' })
  const semesterTab = screen.getByRole('tab', { name: 'Semesters' })
  expect(semesterTab).toHaveFocus()
  expect(semesterTab).toHaveAttribute('tabindex', '0')
  expect(search).toHaveValue('2026')
  const sidebar = within(screen.getByRole('navigation', { name: 'Academic Setup navigation' }))
  expect(sidebar.getByRole('button', { name: 'Academic Terms', exact: true })).toHaveAttribute('aria-current', 'page')
  fireEvent.click(sidebar.getByRole('button', { name: 'Important Dates', exact: true }))
  expect(screen.getByRole('tab', { name: 'Important Dates' })).toHaveAttribute('aria-selected', 'true')
  expect(search).toHaveValue('2026')
})

it('opens student enrollment from Sections and preserves read-only write guards', async () => {
  structureCatalogue.manageable = []
  vi.mocked(api.getRegistrationCatalogue).mockResolvedValue({
    institution_id: 'institution-1',
    groups: [],
    students: [],
    assignments: [],
    can_assign: false,
    can_manage_choices: false,
  })
  render(<Workspace initial="sections" />)
  fireEvent.click(screen.getByRole('button', { name: 'Manage Student Enrollment', exact: true }))
  await screen.findByRole('heading', { name: 'Student Enrollment', level: 1 })
  await waitFor(() => expect(screen.getByText(/Assigning students requires/)).toBeInTheDocument())
  expect(screen.queryByRole('button', { name: 'Assign student', exact: true })).not.toBeInTheDocument()
})

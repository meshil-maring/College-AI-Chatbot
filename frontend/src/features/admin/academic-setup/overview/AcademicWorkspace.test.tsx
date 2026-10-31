import '../__tests__/AcademicSetup.support.ts'
import {
  auth,
  catalogue,
  department,
  program,
  setCatalogue,
  structureCatalogue,
} from '../__tests__/AcademicSetup.support.ts'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../../services/admin/academics.ts'
import AcademicWorkspace from './AcademicWorkspace.tsx'
import AcademicSidebar from './AcademicSidebar.tsx'
import AcademicSearch from './AcademicSearch.tsx'
import type { AcademicPage } from './academicOverviewModel.ts'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import { populateStructure } from '../__tests__/academicStructureFixtures.ts'

function Workspace() {
  const [page, setPage] = useState<AcademicPage>('overview')
  const [search, setSearch] = useState('')
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicSearch
        value={search}
        onChange={(value) => {
          setSearch(value)
          setPage('overview')
        }}
      />
      <AcademicWorkspace page={page} search={search} onNavigate={setPage} onClearSearch={() => setSearch('')} />
    </>
  )
}

describe('Academic Setup overview', () => {
  it('represents all eleven entities and keeps the important relationships distinct', async () => {
    render(<Workspace />)
    const nav = screen.getByRole('navigation', { name: 'Academic Setup navigation' })
    for (const name of [
      'Departments',
      'Programs',
      'Academic Years',
      'Academic Terms',
      'Subjects',
      'Curriculum Versions',
      'Subjects by semester',
      'Subjects by section',
      'Batches',
      'Academic Sections',
    ]) {
      expect(within(nav).getByRole('button', { name, exact: true })).toBeInTheDocument()
    }
    expect(within(nav).queryByRole('button', { name: 'Program Semesters', exact: true })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Academic Setup', level: 1 })).toBeInTheDocument()
    expect(screen.getByText(/one program semester and one academic term/)).toBeInTheDocument()
    fireEvent.click(within(nav).getByRole('button', { name: 'Academic Sections', exact: true }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Sections')
    expect(screen.getByRole('region', { name: 'Section records' })).toBeInTheDocument()
    fireEvent.click(within(nav).getByRole('button', { name: 'Subjects by section', exact: true }))
    expect(await screen.findByRole('heading', { name: 'Subjects by section', level: 1 })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Subjects by semester' })).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Choose an academic section' })).toBeInTheDocument()
    fireEvent.click(within(nav).getByRole('button', { name: 'Subjects by semester', exact: true }))
    expect(await screen.findByRole('heading', { name: 'Subjects by semester', level: 1 })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('uses verified tenant counts and distinguishes unavailable data from confirmed zero', async () => {
    catalogue.records.departments!.push({ ...department, department_id: 'foreign', institution_id: 'foreign' })
    render(<Workspace />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeEnabled())
    const summary = screen.getByRole('region', { name: 'Academic summary' })
    expect(within(summary).getByRole('button', { name: /Departments/ })).toHaveTextContent('1Active departments')
    expect(within(summary).getByRole('button', { name: /Programs/ })).toHaveTextContent('0Active programs')
    expect(within(summary).getByRole('button', { name: /Subjects/ })).toHaveTextContent('—Unavailable')
  })

  it('recommends the next missing setup step from saved records', async () => {
    catalogue.records.programs = [{ ...program, institution_id: 'foreign' }]
    catalogue.records.courses = []
    render(<Workspace />)
    const progress = await screen.findByRole('region', { name: 'Academic setup progress' })
    expect(await within(progress).findByRole('heading', { name: 'Set up a program' })).toBeInTheDocument()
    expect(within(progress).getByRole('button', { name: 'Set up a program' })).toBeInTheDocument()
    fireEvent.click(within(progress).getByRole('button', { name: 'Set up a program' }))
    expect(await screen.findByRole('heading', { name: 'Programs', level: 1 })).toBeInTheDocument()
  })

  it('shows completed readiness for the selected program and keeps class delivery explicitly optional', async () => {
    populateStructure()
    render(<Workspace />)
    const progress = await screen.findByRole('region', { name: 'Academic setup progress' })
    expect(
      await within(progress).findByRole('heading', { name: 'Enroll students in this program’s sections' }),
    ).toBeInTheDocument()
    expect(within(progress).getByText(/Class sections aren’t needed to prepare a curriculum/)).toBeInTheDocument()
    expect(within(progress).getByText(/1 active reusable subject · 1 active academic year/)).toBeInTheDocument()
    expect(within(progress).getByText(/1 active batch/)).toBeInTheDocument()
  })

  it('searches separate curriculum destinations and tenant-readable record names', async () => {
    catalogue.records.departments!.push({
      ...department,
      name: 'Foreign Biology',
      code: 'BIO',
      institution_id: 'foreign',
    })
    render(<Workspace />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeEnabled())
    const search = screen.getByRole('searchbox')
    fireEvent.change(search, { target: { value: 'curricula' } })
    const results = screen.getByRole('region', { name: 'Academic management areas' })
    expect(within(results).getByRole('heading', { name: 'Curriculum Versions' })).toBeInTheDocument()
    expect(within(results).getByRole('heading', { name: 'Subjects by semester' })).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'subject options' } })
    expect(within(results).getByRole('heading', { name: 'Subjects by semester' })).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'CSE' } })
    expect(within(results).getByRole('button', { name: /Computer Science and Engineering/ })).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'Foreign Biology' } })
    expect(within(results).getByRole('heading', { name: 'No academic areas found' })).toBeInTheDocument()
    fireEvent.click(within(results).getByRole('button', { name: 'Clear search' }))
    expect(search).toHaveValue('')
    expect(within(results).getAllByRole('article')).toHaveLength(7)
  })

  it('opens an authorized quick action in the existing form without creating anything', async () => {
    render(<Workspace />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Program', exact: true })).toBeEnabled())
    expect(screen.getByRole('button', { name: 'Manage Sections', exact: true })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Add Program', exact: true }))
    expect(await screen.findByRole('form', { name: 'New degree program' })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('hides existing write actions when server grants are read-only', async () => {
    catalogue.manageable = []
    structureCatalogue.manageable = []
    render(<Workspace />)
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Academic summary' })).toHaveAttribute('aria-busy', 'false'),
    )
    expect(screen.queryByRole('button', { name: 'Add Department', exact: true })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add Program', exact: true })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Manage Curriculum Versions', exact: true })).toBeDisabled()
  })
  it('mounts quick actions only while expanded and closes them with Escape', async () => {
    render(<Workspace />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeEnabled())
    const summary = screen.getByText('Quick Actions')
    fireEvent.click(summary)
    await waitFor(() => expect(summary).toHaveAttribute('aria-expanded', 'true'))
    expect(screen.getAllByRole('button', { name: 'Add Department', exact: true })).toHaveLength(2)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(summary).toHaveAttribute('aria-expanded', 'false')
    expect(summary).toHaveFocus()
    expect(screen.getAllByRole('button', { name: 'Add Department', exact: true })).toHaveLength(1)
  })

  it('shows a recoverable request failure and never substitutes a zero count', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Unavailable'))
    render(<Workspace />)
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded')
    const summary = screen.getByRole('region', { name: 'Academic summary' })
    expect(within(summary).getByRole('button', { name: /Departments/ })).toHaveTextContent('—Unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeEnabled())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('ignores a late catalogue from a replaced identity', async () => {
    let resolveOld!: (value: AcademicCatalogue) => void
    vi.mocked(api.getAcademicSetup).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve
        }),
    )
    const view = render(<Workspace />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading Academic Setup')
    auth.accessToken = 'new-token'
    auth.user.institution_id = 'new-institution'
    setCatalogue({ institution_id: 'new-institution', records: { departments: [] }, manageable: [] })
    view.rerender(<Workspace />)
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Academic summary' })).toHaveAttribute('aria-busy', 'false'),
    )
    await act(async () =>
      resolveOld({
        institution_id: department.institution_id,
        records: { departments: [department] },
        manageable: ['departments'],
      }),
    )
    expect(screen.queryByRole('button', { name: 'Add Department', exact: true })).not.toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: 'Academic summary' })).getByRole('button', { name: /Departments/ }),
    ).toHaveTextContent('0Active departments')
  })

  it('rejects mismatched tenant data and replaces illustrative activity with saved events', async () => {
    catalogue.institution_id = 'foreign'
    render(<Workspace />)
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable for this institution')
    expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeDisabled()
    expect(screen.getByText('Recent saved changes in readable academic areas.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'View all' }))
    expect(screen.getByText('No recent academic changes.')).toBeInTheDocument()
  })
  it.each([[], ['profile.own.read'], ['departments.manage']])(
    'renders a preview without catalogue requests for grants %j',
    (permissions) => {
      auth.user.effective_permissions = permissions
      render(<Workspace />)
      expect(screen.getByRole('status')).toHaveTextContent('does not have academic catalogue access')
      expect(screen.getByRole('region', { name: 'Academic summary' })).toHaveAttribute('aria-busy', 'false')
      expect(screen.getAllByRole('article')).toHaveLength(7)
      expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeDisabled()
      expect(api.getAcademicSetup).not.toHaveBeenCalled()
    },
  )
  it('does not mount existing record workflows without catalogue read access', () => {
    auth.user.effective_permissions = []
    render(<AcademicWorkspace page="records" search="" onNavigate={vi.fn()} onClearSearch={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Academic Setup', level: 1 })).toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
  })
})

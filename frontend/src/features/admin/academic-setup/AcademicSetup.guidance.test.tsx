import './__tests__/AcademicSetup.support.tsx'
import { fixture, loaded, tab } from './__tests__/AcademicSetup.support.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../../../services/admin/adminApi.ts'
import * as packagesApi from '../../../services/academics/academicPackagesApi.ts'
import AcademicSetup from './AcademicSetup.tsx'

const workflow = () => within(screen.getByRole('navigation', { name: 'Academic setup workflow' }))

describe('guided Academic Setup', () => {
  it('opens degree program setup when subjects exist but no course or branch has been created', async () => {
    const data = fixture()
    data.records.programs = []
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    vi.mocked(packagesApi.getAcademicPackages).mockResolvedValue({
      institution_id: 'tenant',
      capabilities: ['manage_curriculum'],
      records: {},
      options: { programs: [], subjects: data.records.courses ?? [] },
    })
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(workflow().getByRole('button', { name: '4 Curricula & packages' }))
    const branches = await screen.findByLabelText('Course / branch')
    expect(within(branches).getAllByRole('option')).toHaveLength(1)
    expect(screen.getByText(/Subjects are individual papers, such as DSA or ML/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Set up a course / branch' }))
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument()
    expect(screen.getByLabelText('Record type')).toHaveValue('programs')
    expect(await screen.findByRole('button', { name: 'Add Program' })).toBeEnabled()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('presents one six-stage journey and contextual foundational records', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    expect(
      workflow()
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['1College basics', '2Calendar', '3Subjects', '4Curricula & packages', '5Classes', '6Assignments'])
    expect(screen.queryByRole('navigation', { name: 'Academic setup entities' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Academic setup groups' })).not.toBeInTheDocument()
    expect(
      within(screen.getByLabelText('Record type'))
        .getAllByRole('option')
        .map((option) => option.getAttribute('value')),
    ).toEqual(['departments', 'programs', 'batches'])
    tab('Programs')
    expect(screen.queryByRole('button', { name: /Manage Curriculum/ })).not.toBeInTheDocument()
    expect(screen.getByText(/Build this program's subject combinations in Curricula & packages/)).toBeInTheDocument()
  })

  it('guides an empty college through real dependencies without creating data on load', async () => {
    const data = fixture()
    Object.keys(data.records).forEach((key) => {
      data.records[key as keyof typeof data.records] = []
    })
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue(data)
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument()
    tab('Programs')
    expect(screen.getByRole('button', { name: /^Add / })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Open Departments' }))
    expect(screen.getByRole('button', { name: 'Add Department' })).toBeEnabled()
    tab('Semesters')
    expect(screen.getByRole('button', { name: /^Add / })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Open Academic years' }))
    expect(screen.getByRole('button', { name: 'Add Academic Year' })).toBeEnabled()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('embeds each package stage once and keeps requests/history under Assignments', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(workflow().getByRole('button', { name: '4 Curricula & packages' }))
    await screen.findByLabelText('Curriculum')
    expect(screen.queryByRole('navigation', { name: 'Curriculum and package pages' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Assignment operations' })).not.toBeInTheDocument()
    await waitFor(() => expect(workflow().getByRole('button', { name: '5 Classes' })).toBeEnabled())
    fireEvent.click(workflow().getByRole('button', { name: '5 Classes' }))
    await screen.findByLabelText('Shared class')
    expect(screen.queryByRole('button', { name: 'Named curricula & packages' })).not.toBeInTheDocument()
    fireEvent.click(workflow().getByRole('button', { name: '6 Assignments' }))
    const operations = await screen.findByRole('navigation', { name: 'Assignment operations' })
    expect(
      within(operations)
        .getAllByRole('button')
        .map((button) => button.textContent),
    ).toEqual(['Student assignments', 'Change Requests', 'History'])
    expect(screen.queryByRole('button', { name: /^Course Offerings/ })).not.toBeInTheDocument()
  })

  it('keeps unsaved foundational forms in place until saved or cancelled', async () => {
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add Department' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'Unsaved' } })
    expect(workflow().getByRole('button', { name: '2 Calendar' })).toBeDisabled()
    expect(screen.getByLabelText('Record type')).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next: Calendar' }))
    expect(screen.getByText('Step 2 of 6')).toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('preserves help descriptions, keyboard dismissal, and tapping without submitting', async () => {
    const user = userEvent.setup()
    render(<AcademicSetup accessToken="jwt" />)
    await loaded()
    fireEvent.click(screen.getByRole('button', { name: 'Add Department' }))
    expect(screen.getByLabelText('Name *')).toHaveAccessibleDescription(
      'Enter the official name, for example Computer Science.',
    )
    const help = screen.getByRole('button', { name: 'Help for Name' })
    fireEvent.focus(help)
    expect(screen.getByRole('tooltip')).toHaveTextContent('Enter the official name')
    fireEvent.keyDown(help, { key: 'Escape' })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    fireEvent.blur(help)
    await user.click(help)
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    await user.click(help)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    expect(api.saveAcademicRecord).not.toHaveBeenCalled()
  })

  it('explains projected read-only dependencies without exposing hidden editors', async () => {
    vi.mocked(api.getAcademicCatalogue).mockResolvedValue({
      institution_id: 'tenant',
      manageable: ['courses'],
      records: { courses: [] },
    })
    render(<AcademicSetup accessToken="jwt" />)
    await screen.findByText('Your role has no access to these college records.')
    fireEvent.click(workflow().getByRole('button', { name: '3 Subjects' }))
    await screen.findByRole('button', { name: 'Add Subject' })
    expect(screen.getByRole('button', { name: 'Add Subject' })).toBeDisabled()
    expect(screen.getByText(/Ask an administrator with access to Departments/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open Departments' })).not.toBeInTheDocument()
  })
})

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../services/academics/academicPackagesApi.ts'
import { queryClient } from '../../lib/queryClient.ts'
import AcademicPackagesWorkspace from './AcademicPackagesWorkspace.tsx'
import { assignedCatalogue, catalogue } from './__tests__/fixtures.ts'
import { isLocked } from './packagePresentation.ts'
import { buildStudentNavigation } from '../student/workspace/studentNavigation.ts'
import { buildFacultyNavigation } from '../faculty/workspace/facultyNavigation.ts'
import { buildStaffNavigation } from '../staff/staffNavigation.ts'

vi.mock('../../services/academics/academicPackagesApi.ts')

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  vi.mocked(api.getAcademicPackages).mockResolvedValue(catalogue())
  vi.mocked(api.commandAcademicPackage).mockResolvedValue({})
})
afterEach(() => queryClient.clear())

async function openClass() {
  await screen.findByLabelText('Class')
  fireEvent.change(screen.getByLabelText('Class'), { target: { value: 'class' } })
}

it('previews shared core plus complete package and submits one initial assignment', async () => {
  render(<AcademicPackagesWorkspace accessToken="token" />)
  await openClass()
  fireEvent.change(screen.getByLabelText('Student class placement'), { target: { value: 'placement' } })
  fireEvent.change(screen.getByLabelText('Complete package'), { target: { value: 'abc' } })
  const preview = screen.getByLabelText('Complete package subjects')
  expect(within(preview).getByText(/Data Structures/)).toBeInTheDocument()
  expect(within(preview).getByText(/Machine Learning/)).toBeInTheDocument()
  expect(within(preview).getByText(/Subject A/)).toBeInTheDocument()
  expect(within(preview).queryByText(/Subject E/)).not.toBeInTheDocument()
  fireEvent.submit(screen.getByRole('form', { name: 'Initial package assignment' }))
  await waitFor(() =>
    expect(api.commandAcademicPackage).toHaveBeenCalledWith('token', 'assign_package', {
      placement_id: 'placement',
      package_id: 'abc',
    }),
  )
})

it('keeps first-time student selection unavailable when administration disables it', async () => {
  const data = catalogue()
  data.records.classes![0].student_choice_enabled = false
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" />)
  await openClass()
  expect(screen.getByText(/Your administration assigns the initial package/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Assign all package subjects' })).not.toBeInTheDocument()
})

it('students request a later complete change while keeping the current assignment', async () => {
  vi.mocked(api.getAcademicPackages).mockResolvedValue(assignedCatalogue())
  render(<AcademicPackagesWorkspace accessToken="token" />)
  await openClass()
  fireEvent.change(screen.getByLabelText('Assignment'), { target: { value: 'assignment' } })
  expect(screen.queryByRole('form', { name: 'Initial package assignment' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Apply complete package change' })).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Requested package'), { target: { value: 'efg' } })
  fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Choose a different elective pathway' } })
  fireEvent.submit(screen.getByRole('form', { name: 'Request package change' }))
  await waitFor(() =>
    expect(api.commandAcademicPackage).toHaveBeenCalledWith('token', 'request_change', {
      assignment_id: 'assignment',
      package_id: 'efg',
      reason: 'Choose a different elective pathway',
    }),
  )
  expect(screen.getByText(/Revision 3/)).toBeInTheDocument()
})

it('shows a hard lock for existing assignments, including administrative changes', async () => {
  const data = assignedCatalogue()
  data.capabilities = ['assign', 'change']
  data.records.classes![0].change_cutoff = '2020-01-01T00:00:00Z'
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" />)
  await openClass()
  fireEvent.change(screen.getByLabelText('Assignment'), { target: { value: 'assignment' } })
  expect(screen.getByText(/Package changes closed on/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Apply complete package change' })).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Requested package')).not.toBeInTheDocument()
})

it('uses expected revision for administrative changes and reports rejected writes', async () => {
  const data = assignedCatalogue()
  data.capabilities = ['assign', 'change']
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  vi.mocked(api.commandAcademicPackage).mockRejectedValue(new Error('Assignment changed. Refresh before trying again.'))
  render(<AcademicPackagesWorkspace accessToken="token" />)
  await openClass()
  fireEvent.change(screen.getByLabelText('Assignment'), { target: { value: 'assignment' } })
  fireEvent.change(screen.getByLabelText('Requested package'), { target: { value: 'efg' } })
  fireEvent.change(screen.getByLabelText('Reason'), { target: { value: 'Approved subject plan change' } })
  fireEvent.submit(screen.getByRole('form', { name: 'Change assigned package' }))
  await waitFor(() =>
    expect(api.commandAcademicPackage).toHaveBeenCalledWith('token', 'change_package', {
      assignment_id: 'assignment',
      package_id: 'efg',
      expected_revision: 3,
      reason: 'Approved subject plan change',
    }),
  )
  expect(await screen.findByRole('alert')).toHaveTextContent('Assignment changed')
  expect(screen.getByText(/Revision 3/)).toBeInTheDocument()
})

it('authorized reviewers submit an explicit decision with a reason', async () => {
  const data = assignedCatalogue()
  data.capabilities = ['review']
  data.records.requests = [
    {
      request_id: 'request',
      assignment_id: 'assignment',
      package_id: 'efg',
      reason: 'Preferred electives',
      status: 'pending',
    },
  ]
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" />)
  fireEvent.click(await screen.findByRole('button', { name: 'Change Requests' }))
  fireEvent.change(screen.getByLabelText('Decision'), { target: { value: 'reject' } })
  fireEvent.change(screen.getByLabelText('Reason'), {
    target: { value: 'Discuss this study plan with the coordinator' },
  })
  fireEvent.submit(screen.getByRole('form', { name: 'Review change request' }))
  await waitFor(() =>
    expect(api.commandAcademicPackage).toHaveBeenCalledWith('token', 'review_request', {
      request_id: 'request',
      approve: false,
      reason: 'Discuss this study plan with the coordinator',
    }),
  )
})

it('treats the exact cutoff boundary and server lock as closed', () => {
  const cutoff = '2026-10-21T10:00:00Z'
  expect(isLocked({ change_cutoff: cutoff }, Date.parse(cutoff) - 1)).toBe(false)
  expect(isLocked({ change_cutoff: cutoff }, Date.parse(cutoff))).toBe(true)
  expect(isLocked({ change_cutoff: cutoff, changes_locked: true }, Date.parse(cutoff) - 1)).toBe(true)
})

it('discovers package workspaces from own, delegated, and scoped permissions', () => {
  expect(buildStudentNavigation('student', ['academic.package.own.read']).map((item) => item.key)).toEqual(['packages'])
  expect(buildStaffNavigation('staff', ['academic.package.assign']).map((item) => item.key)).toEqual([
    'academic-packages',
  ])
  expect(buildFacultyNavigation('faculty', [], ['academic.package.requests.review']).map((item) => item.key)).toContain(
    'academic-packages',
  )
  expect(buildFacultyNavigation('faculty', []).map((item) => item.key)).not.toContain('academic-packages')
})

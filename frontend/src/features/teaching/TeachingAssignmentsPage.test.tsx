import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../lib/queryClient.ts'
import * as api from '../../services/academics/teachingApi.ts'
import type { TeachingAssignment, TeachingAssignments, TeachingOptions } from '../../types/teaching.ts'
import TeachingAssignmentsPage from './TeachingAssignmentsPage.tsx'

vi.mock('../../services/academics/teachingApi.ts')

const CSE = 'd-cse'
const MECH = 'd-mech'
const DATABASES = {
  academic_offering_id: 'o-1',
  subject_code: 'CS201',
  subject_name: 'Databases',
  section_code: 'CSE-2A',
  section_name: 'CSE Year 2 A',
  semester_name: 'Semester 3',
  department_id: CSE,
  department_name: 'Computer Science',
}
const THERMO = {
  ...DATABASES,
  academic_offering_id: 'o-2',
  subject_code: 'ME201',
  subject_name: 'Thermodynamics',
  department_id: MECH,
  department_name: 'Mechanical',
}
const OPTIONS: TeachingOptions = {
  institution_id: 't-1',
  offerings: [DATABASES, THERMO],
  faculty: [{ user_id: 'f-1', name: 'Tina Teacher', department_ids: [CSE] }],
}

function assignment(changes: Partial<TeachingAssignment> = {}): TeachingAssignment {
  return {
    ...THERMO,
    assignment_id: 'a-1',
    status: 'pending',
    needs_approval: true,
    is_current: false,
    faculty_user_id: 'f-1',
    faculty_name: 'Tina Teacher',
    starts_on: '2026-11-22',
    planned_end_on: null,
    requested_by_name: 'Olive Owner',
    requested_at: '2026-11-22T10:00:00Z',
    decided_by_name: null,
    decided_at: null,
    decision_note: null,
    ended_at: null,
    can_decide: true,
    can_end: true,
    ...changes,
  }
}

function overview(changes: Partial<TeachingAssignments> = {}): TeachingAssignments {
  return { institution_id: 't-1', is_admin: false, head_department_ids: [MECH], assignments: [], ...changes }
}

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  vi.mocked(api.getTeachingOptions).mockResolvedValue(OPTIONS)
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

describe('Teaching assignments', () => {
  it('assigns home-department teaching at once and says when approval is needed', async () => {
    vi.mocked(api.getTeachingAssignments).mockResolvedValue(overview({ is_admin: true, head_department_ids: [] }))
    vi.mocked(api.requestTeachingAssignment).mockResolvedValue({
      assignment_id: 'a-9',
      status: 'pending',
      already_applied: false,
    })
    render(<TeachingAssignmentsPage accessToken="jwt" />)
    const form = await screen.findByRole('form', { name: 'Assign teaching' })
    await within(form).findByRole('option', { name: /Thermodynamics/ })
    fireEvent.change(within(form).getByLabelText('Faculty member'), { target: { value: 'f-1' } })
    fireEvent.change(within(form).getByLabelText('Subject and class'), { target: { value: 'o-1' } })
    expect(within(form).getByRole('button', { name: 'Assign' })).toBeEnabled()
    fireEvent.change(within(form).getByLabelText('Subject and class'), { target: { value: 'o-2' } })
    expect(within(form).getByText(/waits for the Mechanical Head of Department/)).toBeInTheDocument()
    fireEvent.click(within(form).getByRole('button', { name: 'Send for approval' }))
    await waitFor(() =>
      expect(api.requestTeachingAssignment).toHaveBeenCalledWith('jwt', {
        academic_offering_id: 'o-2',
        faculty_user_id: 'f-1',
        starts_on: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        planned_end_on: null,
      }),
    )
    expect(await screen.findByText(/Request sent/)).toBeInTheDocument()
  })

  it('lets the receiving HOD approve, and asks for a reason to reject', async () => {
    vi.mocked(api.getTeachingAssignments).mockResolvedValue(overview({ assignments: [assignment()] }))
    vi.mocked(api.decideTeachingAssignment).mockResolvedValue({
      assignment_id: 'a-1',
      status: 'rejected',
      already_applied: false,
    })
    render(<TeachingAssignmentsPage accessToken="jwt" />)
    const requests = await screen.findByRole('region', { name: /Requests waiting for you/ })
    fireEvent.click(within(requests).getByRole('button', { name: 'Reject…' }))
    const reject = within(requests).getByRole('button', { name: 'Reject request' })
    expect(reject).toBeDisabled()
    fireEvent.change(within(requests).getByLabelText('Reason for rejecting'), { target: { value: 'Timetable clash' } })
    fireEvent.click(reject)
    await waitFor(() =>
      expect(api.decideTeachingAssignment).toHaveBeenCalledWith('jwt', 'a-1', 'reject', 'Timetable clash'),
    )
    expect(await screen.findByText(/Rejected: Tina Teacher/)).toBeInTheDocument()
  })

  it('stops a HOD from choosing teaching outside their departments', async () => {
    vi.mocked(api.getTeachingAssignments).mockResolvedValue(overview({ head_department_ids: ['d-civil'] }))
    render(<TeachingAssignmentsPage accessToken="jwt" />)
    const form = await screen.findByRole('form', { name: 'Assign teaching' })
    await within(form).findByRole('option', { name: /Databases/ })
    fireEvent.change(within(form).getByLabelText('Faculty member'), { target: { value: 'f-1' } })
    fireEvent.change(within(form).getByLabelText('Subject and class'), { target: { value: 'o-1' } })
    expect(within(form).getByText(/only in departments you head/)).toBeInTheDocument()
    expect(within(form).getByRole('button', { name: 'Assign' })).toBeDisabled()
  })

  it('lists current teaching, ends it after confirming and keeps history', async () => {
    const current = assignment({ status: 'active', is_current: true, can_decide: false, needs_approval: false })
    const old = assignment({ assignment_id: 'a-2', status: 'ended', ended_at: '2026-10-01T00:00:00Z', can_end: false })
    vi.mocked(api.getTeachingAssignments).mockResolvedValue(overview({ assignments: [current, old] }))
    vi.mocked(api.endTeachingAssignment).mockResolvedValue({
      assignment_id: 'a-1',
      status: 'ended',
      already_applied: false,
    })
    render(<TeachingAssignmentsPage accessToken="jwt" />)
    const list = await screen.findByRole('list', { name: 'Teaching assignments' })
    expect(within(list).getAllByRole('listitem')).toHaveLength(1)
    expect(within(list).getByText('Teaching')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show history (1)' }))
    expect(within(list).getAllByRole('listitem')).toHaveLength(2)
    fireEvent.click(within(list).getByRole('button', { name: 'End Tina Teacher teaching Thermodynamics (CSE-2A)' }))
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('The record is kept.'))
    await waitFor(() => expect(api.endTeachingAssignment).toHaveBeenCalledWith('jwt', 'a-1'))
    expect(await screen.findByText('Teaching ended.')).toBeInTheDocument()
  })

  it('shows the server refusal when the viewer is not an administrator or HOD', async () => {
    vi.mocked(api.getTeachingAssignments).mockRejectedValue(
      new Error('Only administrators and Heads of Department manage teaching assignments.'),
    )
    render(<TeachingAssignmentsPage accessToken="jwt" />)
    expect(await screen.findByText(/Only administrators and Heads of Department/)).toBeInTheDocument()
  })
})

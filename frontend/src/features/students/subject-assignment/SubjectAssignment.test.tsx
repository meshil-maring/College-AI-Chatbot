import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { facultyStudentWorkspaceApi } from '../../../services/students/studentWorkspaceApi.ts'
import type {
  SubjectAssignmentResult,
  SubjectAssignmentStudent,
} from '../../../services/students/studentRegistrationApi.ts'
import { StudentWorkspaceContext } from '../StudentWorkspaceContext.tsx'
import SubjectAssignment from './SubjectAssignment.tsx'

const student: SubjectAssignmentStudent = {
  registration_id: 'registration',
  student_name: 'Ada Rao',
  register_number: 'CS001',
  university_roll_number: null,
  email: 'ada@college.edu',
  program_id: 'program',
  batch_id: 'batch',
  section_code: 'A',
  batch_start_year: 2026,
  batch_end_year: 2030,
  roster_status: 'UNREGISTERED',
  linked_student_id: null,
  identity_conflict: false,
  subjects_assigned: false,
  assignment_errors: [],
}
const assignment = {
  assignment_id: 'assignment',
  section_id: 'section',
  semester_id: 'semester',
  academic_year_id: 'year',
  assigned_at: '',
  can_manage: true,
  section: { section_id: 'section', code: 'A', name: 'Section A', course: { code: 'CS101', name: 'Computing' } },
}
const api = {
  ...facultyStudentWorkspaceApi,
  getSubjectAssignmentStudents: vi.fn<typeof facultyStudentWorkspaceApi.getSubjectAssignmentStudents>(),
  assignStudentSubject: vi.fn<typeof facultyStudentWorkspaceApi.assignStudentSubject>(),
}

function Page({ canManage = true, sectionId = 'section' }) {
  return (
    <StudentWorkspaceContext.Provider value={api}>
      <SubjectAssignment
        key={sectionId}
        token="token"
        assignment={{ ...assignment, section_id: sectionId, can_manage: canManage }}
        batchId="batch"
      />
    </StudentWorkspaceContext.Provider>
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getSubjectAssignmentStudents.mockResolvedValue({ items: [student], total: 1 })
  api.assignStudentSubject.mockResolvedValue({
    registration_id: 'registration',
    roster_id: 'roster',
    status: 'assigned',
  })
})

it('assigns the saved registration to the selected subject and removes it after refresh', async () => {
  const user = userEvent.setup()
  let finish!: (result: SubjectAssignmentResult) => void
  api.assignStudentSubject.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  render(<Page />)
  const assign = await screen.findByRole('button', { name: 'Assign Ada Rao to CS101 · Computing' })
  await waitFor(() => expect(assign).toBeEnabled())
  await user.click(assign)
  expect(api.assignStudentSubject).toHaveBeenCalledExactlyOnceWith('token', 'section', 'registration')
  expect(assign).toBeDisabled()
  const readsBeforeSearch = api.getSubjectAssignmentStudents.mock.calls.length
  await user.type(screen.getByRole('searchbox'), 'Ada')
  await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
  expect(assign).toBeDisabled()
  expect(api.getSubjectAssignmentStudents).toHaveBeenCalledTimes(readsBeforeSearch)
  api.getSubjectAssignmentStudents.mockResolvedValue({ items: [], total: 0 })
  finish({ registration_id: 'registration', roster_id: 'roster', status: 'assigned' })
  expect(await screen.findByText('Ada Rao was assigned to this subject.')).toBeInTheDocument()
  expect(await screen.findByText('No unassigned students')).toBeInTheDocument()
  expect(api.getSubjectAssignmentStudents).toHaveBeenCalledWith('token', 'section', 0, { batchId: 'batch', search: '' })
})

it('supports searching and paging without dropping the selected batch', async () => {
  const user = userEvent.setup()
  api.getSubjectAssignmentStudents.mockResolvedValue({ items: [student], total: 26 })
  render(<Page />)
  const next = await screen.findByRole('button', { name: 'Next students' })
  await waitFor(() => expect(next).toBeEnabled())
  await user.click(next)
  await waitFor(() =>
    expect(api.getSubjectAssignmentStudents).toHaveBeenLastCalledWith('token', 'section', 25, {
      batchId: 'batch',
      search: '',
    }),
  )
  await user.type(screen.getByRole('searchbox'), 'Ada')
  await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
  await waitFor(() =>
    expect(api.getSubjectAssignmentStudents).toHaveBeenLastCalledWith('token', 'section', 0, {
      batchId: 'batch',
      search: 'Ada',
    }),
  )
})

it('blocks assignment for read-only sections and reports conflicting identifiers', async () => {
  api.getSubjectAssignmentStudents.mockResolvedValue({
    items: [{ ...student, assignment_errors: ['Identity review required.'] }],
    total: 1,
  })
  const view = render(<Page />)
  expect(await screen.findByText('Identity review required.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^Assign Ada/ })).toBeDisabled()
  view.unmount()
  api.getSubjectAssignmentStudents.mockResolvedValue({ items: [student], total: 1 })
  render(<Page canManage={false} />)
  expect(await screen.findByText(/Assigning subjects requires permission/)).toBeInTheDocument()
  fireEvent.click(await screen.findByRole('button', { name: /^Assign Ada/ }))
  expect(api.assignStudentSubject).not.toHaveBeenCalled()
})

it('shows save errors and lets the user retry', async () => {
  const user = userEvent.setup()
  api.assignStudentSubject.mockRejectedValueOnce(new Error('Section access expired'))
  render(<Page />)
  const assign = await screen.findByRole('button', { name: /^Assign Ada/ })
  await waitFor(() => expect(assign).toBeEnabled())
  await user.click(assign)
  expect(await screen.findByRole('alert')).toHaveTextContent('Section access expired')
  api.getSubjectAssignmentStudents.mockResolvedValue({ items: [], total: 0 })
  await user.click(assign)
  expect(await screen.findByText('Ada Rao was assigned to this subject.')).toBeInTheDocument()
})

it('hides previous rows while changing subjects or when the refreshed read is denied', async () => {
  const view = render(<Page />)
  await screen.findByText('Ada Rao')
  api.getSubjectAssignmentStudents.mockRejectedValue(new Error('Subject unavailable'))
  view.rerender(<Page sectionId="other-subject" />)
  expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
  expect(await screen.findByRole('alert')).toHaveTextContent('Subject unavailable')
  expect(screen.queryByRole('button', { name: /^Assign Ada/ })).not.toBeInTheDocument()
  api.getSubjectAssignmentStudents.mockResolvedValue({ items: [student], total: 1 })
  await userEvent.click(screen.getByRole('button', { name: 'Retry students' }))
  expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
})

it('hides stale student rows if a refresh loses access to the same subject', async () => {
  render(<Page />)
  await screen.findByText('Ada Rao')
  api.getSubjectAssignmentStudents.mockRejectedValue(new Error('Access revoked'))
  await userEvent.click(screen.getByRole('button', { name: 'Refresh students' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Access revoked')
  expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^Assign Ada/ })).not.toBeInTheDocument()
})

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../services/academics/academicPackagesApi.ts'
import { queryClient } from '../../lib/queryClient.ts'
import AcademicPackagesWorkspace from './AcademicPackagesWorkspace.tsx'
import { assignedCatalogue, catalogue } from './__tests__/fixtures.ts'

vi.mock('../../services/academics/academicPackagesApi.ts')

beforeEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
  vi.mocked(api.commandAcademicPackage).mockResolvedValue({})
})
afterEach(() => queryClient.clear())

it('prepares teaching groups only when the server grants the preparation capability', async () => {
  const data = catalogue()
  data.capabilities = ['manage_class', 'prepare_teaching']
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  const view = render(<AcademicPackagesWorkspace accessToken="token" initialView="classes" />)
  fireEvent.change(await screen.findByLabelText('Shared class'), { target: { value: 'class' } })
  fireEvent.click(screen.getByRole('button', { name: 'Prepare teaching groups' }))
  await waitFor(() =>
    expect(api.commandAcademicPackage).toHaveBeenCalledWith('token', 'prepare_class_teaching', { class_id: 'class' }),
  )
  view.unmount()
  queryClient.clear()
  vi.mocked(api.getAcademicPackages).mockResolvedValue({ ...data, capabilities: ['manage_class'] })
  render(<AcademicPackagesWorkspace accessToken="other-token" initialView="classes" />)
  fireEvent.change(await screen.findByLabelText('Shared class'), { target: { value: 'class' } })
  expect(screen.queryByRole('button', { name: 'Prepare teaching groups' })).not.toBeInTheDocument()
  expect(screen.getByText(/Ask an administrator with teaching setup access/)).toBeInTheDocument()
})

it('offers class curricula only after a package exists for the selected study semester', async () => {
  const data = catalogue()
  data.capabilities = ['manage_class']
  data.records.packages!.forEach((row) => {
    row.study_semester = 2
  })
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="classes" />)
  const form = await screen.findByRole('form', { name: 'Create shared class' })
  fireEvent.change(within(form).getByLabelText('Course / branch'), { target: { value: 'program' } })
  expect(within(within(form).getByLabelText('Curriculum version')).getAllByRole('option')).toHaveLength(1)
  fireEvent.change(within(form).getByLabelText('Study semester'), { target: { value: '2' } })
  expect(within(within(form).getByLabelText('Curriculum version')).getAllByRole('option')).toHaveLength(2)
  expect(within(form).getByText(/Creating a class freezes this curriculum version/)).toBeInTheDocument()
})

it('offers only incharge responsibilities belonging to mapped teaching sections in the class period', async () => {
  const data = catalogue()
  data.capabilities = ['manage_class']
  data.records.classes![0].academic_year_id = 'year'
  data.records.class_subjects = [{ class_id: 'class', curriculum_subject_id: 'cs-dsa', section_id: 'section' }]
  data.options.sections = [{ section_id: 'section', subject_name: 'Data Structures', name: 'DSA group A' }]
  const responsibility = {
    responsibility_id: 'eligible',
    name: 'Class incharge',
    faculty_email: 'faculty@college.edu',
    program_id: 'program',
    academic_year_id: 'year',
    semester_id: 'term',
    section_id: 'section',
  }
  data.options.responsibilities = [
    responsibility,
    { ...responsibility, responsibility_id: 'other-section', section_id: 'unmapped' },
    { ...responsibility, responsibility_id: 'other-term', semester_id: 'other' },
    { ...responsibility, responsibility_id: 'other-program', program_id: 'other' },
  ]
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="classes" />)
  fireEvent.change(await screen.findByLabelText('Shared class'), { target: { value: 'class' } })
  const options = within(screen.getByLabelText('Existing class incharge responsibility')).getAllByRole('option')
  expect(options).toHaveLength(2)
  expect(options[1]).toHaveValue('eligible')
  expect(options[1]).toHaveTextContent('faculty@college.edu')
  expect(options[1]).toHaveTextContent('DSA group A')
})

it('shows read-only curricula and class detail without management forms', async () => {
  const data = catalogue()
  data.capabilities = []
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="curricula" />)
  fireEvent.change(await screen.findByLabelText('Curriculum'), { target: { value: 'curriculum' } })
  expect(screen.getByRole('heading', { name: /CSE 2026/ })).toBeInTheDocument()
  expect(screen.queryByRole('form', { name: 'Create named curriculum' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Class Setup' }))
  expect(screen.getByLabelText('Shared class')).toBeInTheDocument()
  expect(screen.queryByRole('form', { name: 'Create shared class' })).not.toBeInTheDocument()
})

it('separates class management from curriculum management capabilities', async () => {
  const data = catalogue()
  data.capabilities = ['manage', 'manage_class']
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="curricula" />)
  await screen.findByLabelText('Curriculum')
  expect(screen.queryByRole('form', { name: 'Create named curriculum' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Class Setup' }))
  expect(screen.getByRole('form', { name: 'Create shared class' })).toBeInTheDocument()
})

it('updates initial-choice policy with unchanged exact deadline and class identity', async () => {
  const data = catalogue()
  data.capabilities = ['manage']
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="classes" />)
  fireEvent.change(await screen.findByLabelText('Shared class'), { target: { value: 'class' } })
  const form = screen.getByRole('form', { name: 'Class selection rules' })
  fireEvent.click(within(form).getByLabelText('Allow students to choose their initial package'))
  fireEvent.submit(form)
  await waitFor(() =>
    expect(api.commandAcademicPackage).toHaveBeenCalledWith('token', 'save_class', {
      class_id: 'class',
      program_id: 'program',
      batch_id: 'batch',
      semester_id: 'term',
      study_semester: 1,
      section_code: 'A',
      curriculum_id: 'curriculum',
      student_choice_enabled: false,
      change_cutoff: '2099-10-01T00:00:00Z',
    }),
  )
})

it('keeps the locked cutoff out of editable policy controls', async () => {
  const data = catalogue()
  data.capabilities = ['manage']
  data.records.classes![0].changes_locked = true
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="classes" />)
  fireEvent.change(await screen.findByLabelText('Shared class'), { target: { value: 'class' } })
  const form = screen.getByRole('form', { name: 'Class selection rules' })
  expect(within(form).queryByLabelText('Package change cutoff (IST)')).not.toBeInTheDocument()
  expect(within(form).getByText(/Once closed, it cannot be reopened/)).toBeInTheDocument()
})

it('honors class-specific review and assignment denials inside a wider catalogue', async () => {
  const data = assignedCatalogue()
  data.capabilities = ['assign', 'change', 'review']
  data.records.classes![0].can_assign = false
  data.records.classes![0].can_change = false
  data.records.classes![0].can_review = false
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
  fireEvent.change(await screen.findByLabelText('Class'), { target: { value: 'class' } })
  fireEvent.change(screen.getByLabelText('Assignment'), { target: { value: 'assignment' } })
  expect(screen.queryByRole('form', { name: 'Place registered student in class' })).not.toBeInTheDocument()
  expect(screen.queryByRole('form', { name: 'Change assigned package' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Change Requests' }))
  expect(screen.queryByRole('form', { name: 'Review change request' })).not.toBeInTheDocument()
})

it('renders revision history using the catalogue revision timestamp', async () => {
  const data = assignedCatalogue()
  data.records.history = [
    {
      revision_id: 'revision',
      assignment_id: 'assignment',
      revision: 3,
      package_id: 'abc',
      applied_at: '2026-10-21T09:00:00Z',
      reason: 'Approved plan change',
    },
  ]
  vi.mocked(api.getAcademicPackages).mockResolvedValue(data)
  render(<AcademicPackagesWorkspace accessToken="token" initialView="history" />)
  expect(await screen.findByText('Assignment revision 3')).toBeInTheDocument()
  expect(screen.getByText('Approved plan change')).toBeInTheDocument()
  expect(screen.getByText('2026-10-21T09:00:00Z')).toBeInTheDocument()
})

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentOnboardingPage from './StudentOnboardingPage.tsx'

const mocks = vi.hoisted(() => ({
  createSingle: vi.fn(),
  createBulk: vi.fn(),
  list: vi.fn(),
  reassign: vi.fn(),
  resend: vi.fn(),
  reviewIdentity: vi.fn(),
  getStructure: vi.fn(),
}))

vi.mock('../../../hooks/useApiQuery.ts', () => ({
  useApiQuery: (key: string[], _query: () => unknown, enabled: boolean) => {
    if (!enabled) return { data: undefined, isPending: false, isFetching: false, refetch: vi.fn() }
    return key[2] === 'student-onboarding-structure'
      ? { data: structure, isPending: false, isFetching: false, error: null }
      : { data: { invitations: [] }, isPending: false, isFetching: false, error: null, refetch: vi.fn() }
  },
}))
vi.mock('../../../services/admin/students.ts', () => ({
  createStudentInvitation: mocks.createSingle,
  createStudentInvitationsBulk: mocks.createBulk,
  listStudentInvitations: mocks.list,
  reassignStudentInvitation: mocks.reassign,
  reviewStudentIdentity: mocks.reviewIdentity,
  resendStudentInvitation: mocks.resend,
}))
vi.mock('../../../services/admin/academicStructure.ts', () => ({
  getAcademicStructure: mocks.getStructure,
}))
vi.mock('../students/AdminApprovals.tsx', () => ({
  default: () => <div>Registration request queue</div>,
}))

const structure = {
  records: {
    admission_cohorts: [
      {
        admission_cohort_id: 'batch-1',
        code: 'CSE8777912026',
        name: 'CSE 2026',
        status: 'active',
      },
    ],
    academic_sections: [
      {
        academic_section_id: 'section-1',
        admission_cohort_id: 'batch-1',
        code: 'A',
        name: 'Section A',
        is_active: true,
      },
    ],
  },
}

function renderPage(canReview = false, bulkOnly = false) {
  return render(
    <StudentOnboardingPage
      accessToken="token"
      identity="admin:institution"
      canManage
      canReview={canReview}
      bulkOnly={bulkOnly}
    />,
  )
}

async function chooseSection(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText(/Batch and section/), 'section-1')
}

describe('student onboarding guided workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.createSingle.mockResolvedValue({
      invitation: { email: 'ada@example.com' },
      delivery_status: 'sent',
      delivery_message: 'Setup link sent.',
    })
    mocks.createBulk.mockResolvedValue({
      total: 1,
      created: 1,
      failed: 0,
      rows: [{ row: 2, status: 'created', invitation: null, delivery_status: 'sent', message: 'Link sent.' }],
    })
    mocks.reviewIdentity.mockResolvedValue({
      students: [],
      invitations: [],
      email_conflict_exists: true,
    })
  })

  it('shows registration requests, live invitation metrics, and the admin registration panel', async () => {
    const user = userEvent.setup()
    renderPage(true)

    expect(screen.getByRole('heading', { name: 'Student Registration' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Register Student' })).toHaveAttribute('href', '#student-registration-form')
    expect(screen.getByText('Registration request queue')).toBeInTheDocument()
    expect(screen.getByText('Pending invitations').parentElement).toHaveTextContent('0')
    expect(screen.getByRole('heading', { name: 'Register Student (By Admin)' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Pending Invitations/ }))
    expect(screen.getByRole('status')).toHaveTextContent('No pending student invitations.')
  })

  it('guides single registration through placement, details, review, and confirmation', async () => {
    const user = userEvent.setup()
    renderPage()
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
    expect(screen.getByRole('heading', { name: 'Enter the student’s details' })).toBeInTheDocument()

    await user.type(screen.getByRole('textbox', { name: /Student name/ }), 'Ada Lovelace')
    await user.type(screen.getByRole('textbox', { name: /Register number/ }), 'REG-1')
    await user.type(screen.getByRole('textbox', { name: /Email address/ }), 'ada@example.com')
    expect(screen.queryByRole('button', { name: /Check existing registration/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Review details' }))

    expect(screen.getByText('Academic placement').parentElement).toHaveTextContent('CSE8777912026')
    expect(screen.getByText('Academic placement').parentElement).toHaveTextContent('Section A')
    await user.click(screen.getByRole('button', { name: /Create account & send link/ }))
    expect(await screen.findByText('Student registration is underway')).toBeInTheDocument()
    expect(mocks.createSingle).toHaveBeenCalledWith(
      'token',
      'section-1',
      expect.objectContaining({
        student_name: 'Ada Lovelace',
        register_number: 'REG-1',
      }),
    )
  })

  it('opens bulk import as a focused four-stage page from the student workspace', () => {
    renderPage(false, true)
    expect(screen.getByRole('heading', { name: 'Bulk Student Import' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent(
      'Students›Bulk Import›Academic placement',
    )
    expect(screen.getByRole('list', { name: 'Registration steps' }).children).toHaveLength(4)
    expect(screen.queryByRole('group', { name: 'Choose registration method' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Continue to upload/ })).toBeInTheDocument()
  })

  it('submits registration directly and shows server-side duplicate conflicts', async () => {
    const user = userEvent.setup()
    window.history.replaceState(null, '', '/login/admin')
    mocks.createSingle.mockRejectedValueOnce(
      new Error('Email, Register Number, or University Roll No. is already in use'),
    )
    renderPage()
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to student details/ }))
    await user.type(screen.getByRole('textbox', { name: /Student name/ }), 'Ada Lovelace')
    await user.type(screen.getByRole('textbox', { name: /Register number/ }), 'REG-1')
    await user.type(screen.getByRole('textbox', { name: /Email address/ }), 'ada@example.com')
    expect(screen.queryByRole('button', { name: /Check existing registration/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Review details' }))
    await user.click(screen.getByRole('button', { name: /Create account & send link/ }))
    const conflict = await screen.findByRole('alert')
    expect(conflict).toHaveTextContent('Email, Register Number, or University Roll No. is already in use')
    expect(within(conflict).getByRole('link', { name: 'Open All Students' })).toHaveAttribute(
      'href',
      '/login/admin?view=approvals&student-page=all',
    )
    expect(await within(conflict).findByText(/No matching student or pending invitation was found/)).toBeInTheDocument()
    expect(conflict).toHaveTextContent('that account has no student record here')
    expect(mocks.reviewIdentity).toHaveBeenCalledWith('token', {
      email: 'ada@example.com',
      register_number: 'REG-1',
      university_roll_number: null,
    })
    expect(mocks.createSingle).toHaveBeenCalledOnce()
  })

  it('guides bulk registration through upload, review, and row results', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /Multiple students/ }))
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to upload/ }))
    const file = new File(['Student Name,Register Number,Email\nAda Lovelace,REG-1,ada@example.com'], 'students.csv', {
      type: 'text/csv',
    })
    fireEvent.change(screen.getByLabelText('Choose student CSV or Excel file'), { target: { files: [file] } })
    await user.click(await screen.findByRole('button', { name: /Review student list/ }))
    expect(screen.getByText('1 ready')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Invite 1 ready student/ }))
    expect(await screen.findByRole('heading', { name: 'Student invitations processed' })).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: 'Bulk registration results' })).getByText('Invitations created'),
    ).toBeInTheDocument()
    await waitFor(() => expect(mocks.createBulk).toHaveBeenCalledTimes(1))
  })

  it('filters duplicate and valid rows in the bulk import review', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /Multiple students/ }))
    await chooseSection(user)
    await user.click(screen.getByRole('button', { name: /Continue to upload/ }))
    const file = new File(
      ['Student Name,Register Number,Email\nAda Lovelace,REG-1,ada@example.com\nGrace Hopper,REG-1,grace@example.com'],
      'students.csv',
      { type: 'text/csv' },
    )
    fireEvent.change(screen.getByLabelText('Choose student CSV or Excel file'), { target: { files: [file] } })
    await user.click(await screen.findByRole('button', { name: /Review student list/ }))

    expect(screen.getByRole('button', { name: /Valid 1/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Duplicate 1/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Duplicate 1/ }))
    expect(screen.getByRole('textbox', { name: 'Student Name row 3' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Student Name row 2' })).not.toBeInTheDocument()
  })
})

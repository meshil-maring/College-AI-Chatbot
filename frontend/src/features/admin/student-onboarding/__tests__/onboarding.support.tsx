import { render, screen } from '@testing-library/react'
import type userEvent from '@testing-library/user-event'
import { beforeEach, vi } from 'vitest'
import type { StudentInvitation } from '../../../../types/admin/students.ts'
import StudentOnboardingPage from '../StudentOnboardingPage.tsx'

const hoisted = vi.hoisted(() => ({
  mocks: {
    createSingle: vi.fn(),
    createBulk: vi.fn(),
    list: vi.fn(),
    reassign: vi.fn(),
    resend: vi.fn(),
    reviewIdentity: vi.fn(),
    getStructure: vi.fn(),
    listPending: vi.fn(),
  },
  data: { invitations: [] as unknown[], pendingStudents: [] as unknown[] },
}))
export const mocks = hoisted.mocks
export const queryData = hoisted.data

vi.mock('../../../../hooks/useApiQuery.ts', () => ({
  useApiQuery: (key: string[], _query: () => unknown, enabled = true) => {
    const base = { isPending: false, isFetching: false, error: null, refetch: vi.fn() }
    if (!enabled) return { ...base, data: undefined }
    if (key[2] === 'student-onboarding-structure') return { ...base, data: structure }
    if (key[1] === 'pending-students') return { ...base, data: hoisted.data.pendingStudents }
    return { ...base, data: { invitations: hoisted.data.invitations } }
  },
}))
vi.mock('../../../../services/admin/students.ts', () => ({
  createStudentInvitation: hoisted.mocks.createSingle,
  createStudentInvitationsBulk: hoisted.mocks.createBulk,
  listStudentInvitations: hoisted.mocks.list,
  reassignStudentInvitation: hoisted.mocks.reassign,
  reviewStudentIdentity: hoisted.mocks.reviewIdentity,
  resendStudentInvitation: hoisted.mocks.resend,
}))
vi.mock('../../../../services/admin/academicStructure.ts', () => ({
  getAcademicStructure: hoisted.mocks.getStructure,
}))
vi.mock('../../../../services/admin/adminApi.ts', () => ({
  listPendingStudents: hoisted.mocks.listPending,
}))

export const structure = {
  records: {
    admission_cohorts: [{ admission_cohort_id: 'batch-1', code: 'CSE8777912026', name: 'CSE 2026', status: 'active' }],
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

export function invitation(overrides: Partial<StudentInvitation> = {}): StudentInvitation {
  return {
    invitation_id: 'invite-1',
    institution_id: 'institution',
    academic_section_id: 'section-1',
    section_name: 'Section A',
    section_code: 'A',
    batch_name: 'CSE 2026',
    batch_code: 'CSE8777912026',
    status: 'pending',
    expires_at: '2099-01-01T00:00:00Z',
    created_at: '2026-11-20T00:00:00Z',
    email_delivery_status: 'sent',
    email_delivery_attempts: 1,
    resend_count: 0,
    last_sent_at: '2026-11-20T00:00:00Z',
    student_name: 'Ada Lovelace',
    register_number: 'REG-1',
    university_roll_number: null,
    email: 'ada@example.com',
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  queryData.invitations = []
  queryData.pendingStudents = []
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
  mocks.reviewIdentity.mockResolvedValue({ students: [], invitations: [], email_conflict_exists: false })
})

export function renderPage({ canReview = false, bulkOnly = false } = {}) {
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

export async function chooseSection(user: ReturnType<typeof userEvent.setup>) {
  // A batch with one active section selects that section automatically.
  await user.selectOptions(screen.getByRole('combobox', { name: /Batch/ }), 'batch-1')
}

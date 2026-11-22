import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { StudentSemester } from '../../../types/semesterRegistration.ts'
import type { TransferRequest } from '../../../types/transfer.ts'

const auth = vi.hoisted(() => ({ permissions: ['registration.own.read', 'transfers.read'] as string[] }))
vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { user_id: 'u1', institution_id: 'inst-1', effective_permissions: auth.permissions },
    role: 'student',
    accessToken: 'test-token',
    sessionGeneration: 1,
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))
vi.mock('../../../services/students/studentApi.ts', async (importActual) => ({
  ...(await importActual<typeof import('../../../services/students/studentApi.ts')>()),
  getMyNotices: vi.fn(),
}))
vi.mock('../../../services/academics/semesterRegistration.ts', () => ({ getMySemesters: vi.fn() }))
vi.mock('../../../services/students/transferApi.ts', () => ({ getMyTransfers: vi.fn() }))

import { getMyNotices } from '../../../services/students/studentApi.ts'
import { getMySemesters } from '../../../services/academics/semesterRegistration.ts'
import { getMyTransfers } from '../../../services/students/transferApi.ts'
import StudentDashboard from './StudentDashboard.tsx'
import { pickCurrentSemester, termProgress } from './useDashboardData.ts'
import type { StudentNavItem } from '../workspace/studentNavigation.ts'

const semester = {
  semester_registration_id: 'r1',
  program_name: 'B.Tech (CSE)',
  batch_name: '2023 batch',
  section_name: 'A',
  program_semester_name: 'Semester 6',
  term_name: 'Even 2026',
  start_date: '2026-01-01',
  end_date: '2026-12-31',
  enrolled_subjects: [{ course_id: 'c1', name: 'Machine Learning', code: 'CS601', credits: 4 }],
} as StudentSemester

const request = {
  transfer_request_id: 't1',
  transfer_type: 'section_transfer',
  status: 'under_review',
  from_section: { section_name: 'CSE-A' },
  to_section: { section_name: 'CSE-B' },
} as TransferRequest

const ALL_VIEWS: StudentNavItem[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'registration', label: 'Semester Registration' },
  { key: 'transfer-requests', label: 'Transfer Requests' },
  { key: 'notices', label: 'Notices' },
]

beforeEach(() => {
  vi.resetAllMocks()
  auth.permissions = ['registration.own.read', 'transfers.read']
  vi.mocked(getMySemesters).mockResolvedValue({ institution_id: 'inst-1', items: [semester] })
  vi.mocked(getMyTransfers).mockResolvedValue({
    institution_id: 'inst-1',
    current: null,
    options: [],
    requests: [request, { ...request, transfer_request_id: 't2', status: 'approved' }],
  })
  vi.mocked(getMyNotices).mockResolvedValue({
    total: 1,
    items: [
      {
        notice_id: 'n1',
        title: 'Mid-Sem Examination Schedule',
        content: 'Exams run Nov 24 to Nov 28.',
        category: 'exam',
        priority: 'high',
        is_pinned: false,
        published_at: '2026-11-14T00:00:00Z',
        expires_at: null,
      },
    ],
  })
})

describe('StudentDashboard', () => {
  it('shows real program, semester, notices and open requests', async () => {
    const onNavigate = vi.fn()
    render(<StudentDashboard navigation={ALL_VIEWS} onNavigate={onNavigate} />)
    expect(await screen.findByText('B.Tech (CSE)')).toBeInTheDocument()
    expect(screen.getByText('2023 batch · Section A')).toBeInTheDocument()
    expect(screen.getAllByText('Semester 6').length).toBeGreaterThan(0)
    expect(screen.getByRole('progressbar', { name: 'Term progress' })).toBeInTheDocument()
    expect(await screen.findByText('Mid-Sem Examination Schedule')).toBeInTheDocument()
    expect(getMyNotices).toHaveBeenCalledWith('test-token', 3)

    const requests = screen.getByRole('region', { name: 'Ongoing Requests' })
    expect(await within(requests).findByText('Under review')).toBeInTheDocument()
    expect(within(requests).queryByText('Approved')).not.toBeInTheDocument()

    await userEvent.click(within(requests).getByRole('button', { name: 'View all' }))
    expect(onNavigate).toHaveBeenCalledWith('transfer-requests')
  })

  it('labels widgets without a backend API as coming soon', async () => {
    render(<StudentDashboard navigation={ALL_VIEWS} onNavigate={vi.fn()} />)
    for (const name of ['Attendance', 'CGPA'])
      expect(within(screen.getByRole('region', { name })).getByText('Coming soon')).toBeInTheDocument()
    for (const name of ["Today's Schedule", 'Upcoming Deadlines'])
      expect(within(screen.getByRole('region', { name })).getByText('Coming soon')).toBeInTheDocument()
    const deadlinesLink = within(screen.getByRole('region', { name: 'Upcoming Deadlines' })).getByRole('button', {
      name: 'View all',
    })
    expect(deadlinesLink).toBeDisabled()
    expect(deadlinesLink).toHaveAttribute('title', 'Coming soon')
    const scheduleLink = within(screen.getByRole('region', { name: "Today's Schedule" })).getByRole('button', {
      name: 'View full schedule',
    })
    expect(scheduleLink).toBeDisabled()
    expect(scheduleLink).toHaveAttribute('title', 'Coming soon')
    const attendance = screen.getByRole('region', { name: 'Subject Attendance' })
    expect(await within(attendance).findByText('Machine Learning')).toBeInTheDocument()
    expect(within(attendance).getByText('Coming soon')).toBeInTheDocument()
  })

  it('skips reads the student is not permitted to make', () => {
    auth.permissions = []
    render(<StudentDashboard navigation={[{ key: 'dashboard', label: 'Dashboard' }]} onNavigate={vi.fn()} />)
    expect(screen.getByText('Notices are unavailable for this account.')).toBeInTheDocument()
    expect(screen.getByText('Requests are unavailable for this account.')).toBeInTheDocument()
    expect(getMySemesters).not.toHaveBeenCalled()
    expect(getMyTransfers).not.toHaveBeenCalled()
    expect(getMyNotices).not.toHaveBeenCalled()
  })
})

describe('dashboard helpers', () => {
  it('prefers the running term, else the latest one', () => {
    const later = { ...semester, start_date: '2027-01-01', end_date: '2027-06-30' }
    expect(pickCurrentSemester([later, semester], new Date('2026-06-01'))).toBe(semester)
    expect(pickCurrentSemester([semester, later], new Date('2028-01-01'))).toBe(later)
    expect(pickCurrentSemester([])).toBeNull()
  })
  it('clamps term progress and rejects unusable dates', () => {
    expect(termProgress(semester, new Date('2025-01-01'))).toBe(0)
    expect(termProgress(semester, new Date('2027-06-01'))).toBe(100)
    expect(termProgress({ ...semester, end_date: '2025-01-01' })).toBeNull()
  })
})

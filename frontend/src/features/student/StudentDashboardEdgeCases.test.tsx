/** Phase 6.16.1 — malformed and incomplete payload hardening. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { getMyAcademicProfile } from '../../services/studentApi.ts'
import { getMyAttendanceSummary } from '../../services/studentApi.ts'
import { getMyNotices } from '../../services/studentApi.ts'
import { getMyResources } from '../../services/studentApi.ts'
import { getMyResultsSummary } from '../../services/studentApi.ts'
import { ATTENDANCE, NOTICES, PROFILE, RESOURCES } from './studentTestFixtures.ts'
import { mockAllLoaded } from './studentTestFixtures.ts'

vi.mock('../chat/ChatShell.tsx', () => ({
  default: () => <div data-testid="chat-shell-mock">AI chat</div>,
}))
vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' }, role: 'student',
    accessToken: 'test-token', logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status = 0; code: string | null = null;
  },
  getMyAcademicProfile: vi.fn(), getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(), getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(), getMyResources: vi.fn(),
}))

import StudentDashboard from './StudentDashboard.tsx'

beforeEach(() => { vi.clearAllMocks() })

describe('phase 6.16.1 edge cases', () => {
  it('degrades incomplete identity to placeholders', async () => {
    mockAllLoaded()
    vi.mocked(getMyAcademicProfile).mockResolvedValue({
      ...PROFILE,
      student_number: null, register_number: null,
      university_roll_number: null, email: null,
      institution_name: null, program_name: null, program_code: null,
      academic_year_name: null, current_semester_name: null,
    })
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Welcome')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('shows empty attendance and never a fabricated zero percent', async () => {
    mockAllLoaded()
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      summary: { records_available: false, total_classes: 0, present_classes: 0, absent_classes: 0, late_classes: 0, excused_classes: 0, attendance_percentage: null },
      records: [],
    })
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('No attendance records are available yet.')).toBeInTheDocument()
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
  })

  it('renders malformed percentage as placeholder, never NaN', async () => {
    mockAllLoaded()
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      summary: { records_available: true, total_classes: 5, present_classes: 4, absent_classes: 1, late_classes: 0, excused_classes: 0, attendance_percentage: Number.NaN },
      records: [{ date: '2026-09-04', status: 'present', notes: null }],
    } as unknown as typeof ATTENDANCE)
    render(<StudentDashboard onNavigate={() => {}} />)
    await screen.findByText('Your attendance records')
    expect(screen.queryByText('NaN%')).not.toBeInTheDocument()
    expect(screen.queryByText('NaN')).not.toBeInTheDocument()
  })

  it('renders malformed list payloads as empty states', async () => {
    mockAllLoaded()
    vi.mocked(getMyNotices).mockResolvedValue({ items: null, total: 0 } as unknown as typeof NOTICES)
    vi.mocked(getMyResources).mockResolvedValue({ items: undefined, total: 0 } as unknown as typeof RESOURCES)
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('No recent notices.')).toBeInTheDocument()
    expect(screen.getByText('No learning resources are currently available.')).toBeInTheDocument()
  })

  it('renders duplicate backend rows without invented deduplication', async () => {
    mockAllLoaded()
    vi.mocked(getMyNotices).mockResolvedValue({
      items: [
        { notice_id: 'dup', title: 'Same title', content: 'same', category: 'general', priority: 'normal', is_pinned: false, published_at: '2026-09-01T00:00:00Z', expires_at: null },
        { notice_id: 'dup', title: 'Same title', content: 'same', category: 'general', priority: 'normal', is_pinned: false, published_at: '2026-09-01T00:00:00Z', expires_at: null },
      ],
      total: 2,
    })
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findAllByText('Same title')).toHaveLength(2)
  })

  it('never renders malformed result rows as undefined or object text', async () => {
    mockAllLoaded()
    vi.mocked(getMyResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [{ result_type: { odd: true }, total_credits_earned: Number.NaN, total_credits_max: null, sgpa: Number.NaN, cgpa: null, status: null, issued_at: null }],
    } as unknown as Awaited<ReturnType<typeof getMyResultsSummary>>)
    const { container } = render(<StudentDashboard onNavigate={() => {}} />)
    await screen.findByText('Academic results')
    expect(container.innerHTML).not.toContain('undefined')
    expect(container.innerHTML).not.toContain('[object Object]')
    expect(container.innerHTML).not.toContain('NaN')
  })
})
/** Phase 6.16 — dashboard rendering/empty/loading tests. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  getMyAcademicProfile, getMyAttendanceSummary, getMyNotices,
  getMyResources, getMyResultsSummary, getMyTestResultsSummary,
} from '../../services/studentApi.ts'
import StudentDashboard from './StudentDashboard.tsx'
import { mockAllLoaded, PROFILE } from './studentTestFixtures.ts'

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
beforeEach(() => { vi.clearAllMocks() })

describe('student dashboard rendering', () => {
  it('renders identity, attendance, results, notices, resources, chatbot entry', async () => {
    mockAllLoaded()
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('Midterm 1')).toBeInTheDocument()
    expect(screen.getByText('Exam schedule update')).toBeInTheDocument()
    expect(screen.getByText('Lecture notes week 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open AI Assistant' })).toBeInTheDocument()
  })

  it('shows loading states, never zero/empty claims while loading', async () => {
    vi.mocked(getMyAcademicProfile).mockImplementation(() => new Promise(() => {}))
    vi.mocked(getMyAttendanceSummary).mockImplementation(() => new Promise(() => {}))
    vi.mocked(getMyResultsSummary).mockResolvedValue({ summary: { records_available: false, total_results: 0 }, records: [] })
    vi.mocked(getMyTestResultsSummary).mockResolvedValue({ summary: { records_available: false, total_results: 0 }, records: [] })
    vi.mocked(getMyNotices).mockImplementation(() => new Promise(() => {}))
    vi.mocked(getMyResources).mockImplementation(() => new Promise(() => {}))
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('Loading your profile…')).toBeInTheDocument()
    expect(screen.getByText('Loading your attendance…')).toBeInTheDocument()
    expect(screen.getByText('Loading notices…')).toBeInTheDocument()
    expect(screen.queryByText('No attendance records are available yet.')).not.toBeInTheDocument()
    expect(screen.queryByText('No recent notices.')).not.toBeInTheDocument()
  })

  it('shows empty states when backend has no records', async () => {
    vi.mocked(getMyAcademicProfile).mockResolvedValue({ ...PROFILE, program_name: null, program_code: null })
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      summary: { records_available: false, total_classes: 0, present_classes: 0, absent_classes: 0, late_classes: 0, excused_classes: 0, attendance_percentage: null },
      records: [],
    })
    vi.mocked(getMyResultsSummary).mockResolvedValue({ summary: { records_available: false, total_results: 0 }, records: [] })
    vi.mocked(getMyTestResultsSummary).mockResolvedValue({ summary: { records_available: false, total_results: 0 }, records: [] })
    vi.mocked(getMyNotices).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(getMyResources).mockResolvedValue({ items: [], total: 0 })
    render(<StudentDashboard onNavigate={() => {}} />)
    expect(await screen.findByText('No attendance records are available yet.')).toBeInTheDocument()
    expect(screen.getByText('No examination results are available yet.')).toBeInTheDocument()
    expect(screen.getByText('No recent notices.')).toBeInTheDocument()
    expect(screen.getByText('No learning resources are currently available.')).toBeInTheDocument()
  })
})

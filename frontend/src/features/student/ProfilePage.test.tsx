/** Phase 6.16.3 — Profile page: identity, academic context, read-only, safety. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { getMyAcademicProfile, StudentApiError } from '../../services/studentApi.ts'
import type { StudentAcademicProfile } from '../../types/student.ts'
import { PROFILE } from './studentTestFixtures.ts'

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' },
    role: 'student',
    accessToken: 'test-token',
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status: number
    code: string | null
    constructor(status: number, message: string, _d?: unknown, code?: string | null) {
      super(message)
      this.name = 'StudentApiError'
      this.status = status
      this.code = code ?? null
    }
  },
  getMyAcademicProfile: vi.fn(),
  getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(),
  getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(),
  getMyResources: vi.fn(),
}))

import { ProfilePage } from './StudentPages.tsx'

beforeEach(() => { vi.clearAllMocks() })

describe('phase 6.16.3 profile page', () => {
  it('renders the student identity safely', async () => {
    vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
    render(<ProfilePage />)
    expect(screen.getByRole('heading', { name: 'Your profile' })).toBeInTheDocument()
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(screen.getByText('student@college.edu')).toBeInTheDocument()
    expect(screen.getByText('REG-100')).toBeInTheDocument()
    expect(screen.getByText('ROLL-100')).toBeInTheDocument()
    expect(screen.getByText('STU100')).toBeInTheDocument()
    expect(screen.getByText('Test College')).toBeInTheDocument()
    expect(screen.getByText('TC01')).toBeInTheDocument()
    expect(screen.getByText('Approved')).toBeInTheDocument()
  })

  it('renders the backend-provided academic context', async () => {
    vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
    render(<ProfilePage />)
    expect(await screen.findByRole('heading', { name: 'Academic context' })).toBeInTheDocument()
    expect(screen.getByText('Test College (TC01)')).toBeInTheDocument()
    expect(screen.getByText('B.Tech CSE (CSE)')).toBeInTheDocument()
    expect(screen.getByText('2024-25 (AY24)')).toBeInTheDocument()
    expect(screen.getByText('Semester 3 (S3)')).toBeInTheDocument()
  })
  it('shows the not-provided dash for missing optional fields', async () => {
    vi.mocked(getMyAcademicProfile).mockResolvedValue({
      student_number: null, register_number: 'REG-9', university_roll_number: null,
      email: 's@college.edu', institution_name: null, institution_code: 'TC9',
      program_name: null, program_code: null, academic_year_name: null, academic_year_code: null,
      current_semester_name: null, current_semester_code: null, approval_status: null, status: null,
    } as StudentAcademicProfile)
    render(<ProfilePage />)
    expect(await screen.findByText('REG-9')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(6)
  })

  it('never renders injected internal identifiers', async () => {
    const leaky = {
      ...PROFILE,
      student_id: 'uuid-student', user_id: 'uuid-user',
      institution_id: 'uuid-inst', auth_user_id: 'uuid-auth',
    } as unknown as typeof PROFILE
    vi.mocked(getMyAcademicProfile).mockResolvedValue(leaky)
    const { container } = render(<ProfilePage />)
    await screen.findByText('Welcome, REG-100')
    const html = container.innerHTML
    expect(html).not.toContain('uuid-student')
    expect(html).not.toContain('uuid-user')
    expect(html).not.toContain('uuid-inst')
    expect(html).not.toContain('uuid-auth')
  })

  it('is read-only: no edit controls exist', async () => {
    vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
    const { container } = render(<ProfilePage />)
    await screen.findByText('Welcome, REG-100')
    expect(container.querySelectorAll('input, textarea, select, button')).toHaveLength(0)
    expect(container.textContent).not.toContain('Edit')
    expect(container.textContent).not.toContain('Save')
  })

  it('shows a loading state while the request is in flight', () => {
    vi.mocked(getMyAcademicProfile).mockReturnValue(new Promise(() => {}))
    render(<ProfilePage />)
    expect(screen.getAllByRole('status').length).toBeGreaterThan(0)
  })

  it('recovers with retry when the profile request fails', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyAcademicProfile).mockRejectedValueOnce(new StudentApiError(500, 'down'))
    render(<ProfilePage />)
    expect(await screen.findAllByText('Unable to load your academic profile.').then((els) => els.length)).toBeGreaterThan(0)
    vi.mocked(getMyAcademicProfile).mockResolvedValueOnce(PROFILE)
    await user.click(screen.getAllByRole('button', { name: 'Try again' })[0])
    expect(await screen.findByText('Welcome, REG-100')).toBeInTheDocument()
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(2)
  })
})

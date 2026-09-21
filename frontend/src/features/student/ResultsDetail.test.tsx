/**
 * Phase 6.16.2 — Results detail page tests.
 *
 * Covers: page render, backend-only summary values, both result categories
 * (examination results / test scores) rendered from the existing contracts,
 * the documented filter decision (no client-invented identifiers, exactly one
 * request per category), empty states that never fabricate 0 marks / 0 % /
 * "Fail", loading, independent error + retry, read-only enforcement, incomplete
 * records, data minimization, and responsive table structure.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  getMyAcademicProfile,
  getMyResultsSummary,
  getMyTestResultsSummary,
  StudentApiError,
} from '../../services/studentApi.ts'
import type { StudentOwnResults, StudentOwnTestResults } from '../../types/student.ts'
import { PROFILE, RESULTS, TEST_RESULTS } from './studentTestFixtures.ts'

const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' }, role: 'student',
    accessToken: 'test-token', logout: logoutMock,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status: number; code: string | null
    constructor(status: number, message: string, _d?: unknown, code?: string | null) {
      super(message); this.name = 'StudentApiError'
      this.status = status; this.code = code ?? null
    }
  },
  getMyAcademicProfile: vi.fn(), getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(), getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(), getMyResources: vi.fn(),
}))

import { ResultsDetailPage } from './ResultsDetail.tsx'

/** A newly approved student: no published results of either category yet. */
const NO_RESULTS: StudentOwnResults = {
  summary: { records_available: false, total_results: 0 },
  records: [],
}
const NO_TEST_RESULTS: StudentOwnTestResults = {
  summary: { records_available: false, total_results: 0 },
  records: [],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
  vi.mocked(getMyResultsSummary).mockResolvedValue(RESULTS)
  vi.mocked(getMyTestResultsSummary).mockResolvedValue(TEST_RESULTS)
})

describe('results detail page', () => {
  it('renders academic context, backend summary values, and both categories', async () => {
    render(<ResultsDetailPage />)
    expect(await screen.findByText('Test College (TC01)')).toBeInTheDocument()
    // Backend SGPA/CGPA appear both in the summary and in the record row.
    expect((await screen.findAllByText('8.5')).length).toBeGreaterThan(0) // backend SGPA
    expect(screen.getAllByText('8.2').length).toBeGreaterThan(0) // backend CGPA
    expect(screen.getAllByText('1')).toHaveLength(2) // backend result counts
    const academic = screen.getByRole('table', { name: 'Your published examination results' })
    expect(within(academic).getByText('Semester')).toBeInTheDocument()
    expect(within(academic).getByText('Pass')).toBeInTheDocument()
    const tests = screen.getByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getByText('Midterm 1')).toBeInTheDocument()
    expect(within(tests).getByText('Databases')).toBeInTheDocument()
  })

  it('shows backend marks and percentages verbatim', async () => {
    render(<ResultsDetailPage />)
    const tests = await screen.findByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getByText('42/50')).toBeInTheDocument()
    expect(within(tests).getByText('84%')).toBeInTheDocument()
    expect(within(tests).getByText('A')).toBeInTheDocument()
  })

  it('exposes meaningful column headers for both tables', async () => {
    render(<ResultsDetailPage />)
    const academic = await screen.findByRole('table', { name: 'Your published examination results' })
    expect(within(academic).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      'Result type', 'Credits earned', 'Credits max', 'SGPA', 'CGPA', 'Status', 'Issued',
    ])
    const tests = screen.getByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      'Test', 'Course', 'Marks', 'Grade', 'Conducted',
    ])
  })

  it('loads each category exactly once with no client-invented filter parameters', async () => {
    render(<ResultsDetailPage />)
    await screen.findByRole('table', { name: 'Your published examination results' })
    await screen.findByRole('table', { name: 'Your published test scores' })
    // No academic-year / semester / student identifier is ever sent: the loader
    // receives the access token only, so the server stays authoritative.
    expect(vi.mocked(getMyResultsSummary).mock.calls).toEqual([['test-token']])
    expect(vi.mocked(getMyTestResultsSummary).mock.calls).toEqual([['test-token']])
    expect(vi.mocked(getMyAcademicProfile).mock.calls).toEqual([['test-token']])
  })

  it('renders no filter control (no student-accessible academic-year ids exist)', async () => {
    const { container } = render(<ResultsDetailPage />)
    await screen.findByRole('table', { name: 'Your published examination results' })
    expect(screen.queryByRole('form')).toBeNull()
    expect(container.querySelectorAll('input, select, textarea')).toHaveLength(0)
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})

describe('results detail empty states', () => {
  it('uses neutral wording for a newly approved student with no published results', async () => {
    vi.mocked(getMyResultsSummary).mockResolvedValue(NO_RESULTS)
    vi.mocked(getMyTestResultsSummary).mockResolvedValue(NO_TEST_RESULTS)
    render(<ResultsDetailPage />)
    expect(await screen.findByText('No results are available for this selection.')).toBeInTheDocument()
    expect(screen.getByText('No examination results are available yet.')).toBeInTheDocument()
    expect(screen.getByText('No test scores are available yet.')).toBeInTheDocument()
  })

  it('never fabricates 0, 0% or a Fail verdict from absent data', async () => {
    vi.mocked(getMyResultsSummary).mockResolvedValue(NO_RESULTS)
    vi.mocked(getMyTestResultsSummary).mockResolvedValue(NO_TEST_RESULTS)
    render(<ResultsDetailPage />)
    await screen.findByText('No results are available for this selection.')
    expect(screen.queryByText('0')).toBeNull()
    expect(screen.queryByText('0%')).toBeNull()
    expect(screen.queryByText(/^fail$/i)).toBeNull()
    expect(screen.queryByText(/^pass$/i)).toBeNull()
    expect(screen.queryByText('0/0')).toBeNull()
    expect(screen.queryAllByRole('table')).toHaveLength(0)
  })

  it('keeps one category visible when only the other one is empty', async () => {
    vi.mocked(getMyTestResultsSummary).mockResolvedValue(NO_TEST_RESULTS)
    render(<ResultsDetailPage />)
    expect(
      await screen.findByRole('table', { name: 'Your published examination results' }),
    ).toBeInTheDocument()
    expect(screen.getByText('No test scores are available yet.')).toBeInTheDocument()
    // Category-level emptiness is NOT reported as a page-level empty state.
    expect(screen.queryByText('No results are available for this selection.')).toBeNull()
  })
})

describe('results detail loading, error and retry', () => {
  it('announces loading for each independent category', async () => {
    vi.mocked(getMyResultsSummary).mockReturnValue(new Promise(() => {}))
    vi.mocked(getMyTestResultsSummary).mockReturnValue(new Promise(() => {}))
    render(<ResultsDetailPage />)
    const statuses = await screen.findAllByRole('status')
    const text = statuses.map((node) => node.textContent).join(' ')
    expect(text).toContain('Loading your results')
    expect(text).toContain('Loading examination results')
    expect(text).toContain('Loading test scores')
  })

  it('fails each category independently', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyResultsSummary)
      .mockRejectedValueOnce(new StudentApiError(500, 'Server error', undefined, 'INTERNAL_ERROR'))
      .mockResolvedValueOnce(RESULTS)
    render(<ResultsDetailPage />)
    const alerts = await screen.findAllByRole('alert')
    const announced = alerts.map((node) => node.textContent ?? '').join(' | ')
    expect(announced).toContain('Unable to load examination results.')
    // The untouched category still rendered its backend data.
    const tests = screen.getByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getByText('Midterm 1')).toBeInTheDocument()
    // Retry re-requests ONLY the failed category.
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(
      await screen.findByRole('table', { name: 'Your published examination results' }),
    ).toBeInTheDocument()
    expect(vi.mocked(getMyResultsSummary)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(getMyTestResultsSummary)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(1)
    expect(logoutMock).not.toHaveBeenCalled()
  })

  it('reports a 401 in the affected section without destroying the session', async () => {
    vi.mocked(getMyTestResultsSummary).mockRejectedValue(
      new StudentApiError(401, 'Session expired.', undefined, 'UNAUTHORIZED'),
    )
    render(<ResultsDetailPage />)
    const alerts = await screen.findAllByRole('alert')
    const announced = alerts.map((node) => node.textContent ?? '').join(' | ')
    expect(announced).toContain('Unable to load test scores.')
    expect(logoutMock).not.toHaveBeenCalled()
  })
})

describe('results detail record integrity', () => {
  it('shows the em dash for incomplete records instead of invented values', async () => {
    vi.mocked(getMyResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [{
        result_type: null, total_credits_earned: null, total_credits_max: null,
        sgpa: null, cgpa: null, status: null, issued_at: null,
      }],
    })
    vi.mocked(getMyTestResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [{
        test_name: 'Unit test 1', test_type: null, course_code: null,
        course_name: null, max_marks: null, scored_marks: null,
        percentage: null, letter_grade: null, conducted_at: null,
      }],
    })
    const { container } = render(<ResultsDetailPage />)
    const academic = await screen.findByRole('table', { name: 'Your published examination results' })
    // 6 empty value cells + 1 unknown result type = em dashes, never zeros.
    expect(within(academic).getAllByText('—')).toHaveLength(7)
    const tests = screen.getByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getByText('Unit test 1')).toBeInTheDocument()
    expect(within(tests).getAllByText('—').length).toBeGreaterThan(0)
    expect(container.textContent).not.toContain('NaN')
    expect(container.textContent).not.toContain('undefined')
    expect(container.textContent).not.toContain('null')
  })

  it('falls back to the course code when no course name is provided', async () => {
    vi.mocked(getMyTestResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [{
        test_name: 'Quiz 2', test_type: 'internal', course_code: 'CS302',
        course_name: null, max_marks: 20, scored_marks: 18,
        percentage: 90, letter_grade: 'A+', conducted_at: '2026-08-02',
      }],
    })
    render(<ResultsDetailPage />)
    const tests = await screen.findByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getByText('CS302')).toBeInTheDocument()
    expect(within(tests).getByText('18/20')).toBeInTheDocument()
  })

  it('renders only student-safe fields (no internal identifiers)', async () => {
    vi.mocked(getMyResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [{
        result_type: 'semester', total_credits_earned: 20, total_credits_max: 22,
        sgpa: 8.5, cgpa: 8.2, status: 'pass', issued_at: '2026-08-01',
        result_id: 'res-11111111', student_id: 'stu-22222222',
        institution_id: 'inst-33333333',
      }],
    } as unknown as StudentOwnResults)
    render(<ResultsDetailPage />)
    expect(await screen.findByText('Semester')).toBeInTheDocument()
    expect(screen.queryByText(/11111111|22222222|33333333/)).toBeNull()
  })

  it('keeps wide tables scrollable and the summary grid responsive', async () => {
    const { container } = render(<ResultsDetailPage />)
    const academic = await screen.findByRole('table', { name: 'Your published examination results' })
    expect(academic.parentElement?.className).toContain('overflow-x-auto')
    expect(academic.className).toContain('min-w-')
    const summary = screen.getByText('Latest SGPA').closest('dl')
    expect(summary?.className).toContain('grid-cols-2')
    expect(summary?.className).toContain('sm:grid-cols-4')
    expect(container.firstElementChild?.className).toContain('overflow-x-clip')
  })
})


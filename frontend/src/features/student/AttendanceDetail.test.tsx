/**
 * Phase 6.16.2 — Attendance detail page tests.
 *
 * Covers: render, summary (backend values only), records, server-side date
 * filter, empty state (never implies zero attendance), loading, error/retry,
 * read-only enforcement (no mutation controls), long records, and responsive
 * table structure.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { getMyAcademicProfile, getMyAttendanceSummary, StudentApiError } from '../../services/studentApi.ts'
import type { StudentOwnAttendance } from '../../types/student.ts'
import { ATTENDANCE, PROFILE } from './studentTestFixtures.ts'

const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))

/** What a brand-new approved student legitimately receives: no records at all. */
const NO_RECORDS: StudentOwnAttendance = {
  summary: {
    records_available: false, total_classes: 0, present_classes: 0,
    absent_classes: 0, late_classes: 0, excused_classes: 0,
    attendance_percentage: null,
  },
  records: [],
}

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

import { AttendanceDetailPage } from './AttendanceDetail.tsx'

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
  vi.mocked(getMyAttendanceSummary).mockResolvedValue(ATTENDANCE)
})

describe('attendance detail page', () => {
  it('renders academic context, summary figures, and records', async () => {
    render(<AttendanceDetailPage />)
    expect(await screen.findByText('Test College (TC01)')).toBeInTheDocument()
    expect(await screen.findByText('80%')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Your attendance records' })
    expect(within(table).getAllByRole('row')).toHaveLength(2) // header + one record
    expect(within(table).getByText('Present')).toBeInTheDocument()
  })

  it('renders the backend percentage verbatim (no frontend arithmetic)', async () => {
    // Backend value deliberately differs from present/total so any frontend
    // recomputation would fail this test.
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      summary: { records_available: true, total_classes: 3, present_classes: 1, absent_classes: 1, late_classes: 1, excused_classes: 0, attendance_percentage: 33.33 },
      records: [{ date: '2026-09-01', status: 'present', notes: null }],
    })
    render(<AttendanceDetailPage />)
    expect(await screen.findByText('33.33%')).toBeInTheDocument()
  })

  it('sends server-side date filters as date_from/date_to query params', async () => {
    const user = userEvent.setup()
    render(<AttendanceDetailPage />)
    await screen.findByText('80%')
    await user.type(screen.getByLabelText('From date'), '2026-09-01')
    await user.type(screen.getByLabelText('To date'), '2026-09-30')
    await user.click(screen.getByRole('button', { name: 'Apply date filter' }))
    await vi.waitFor(() => {
      const calls = vi.mocked(getMyAttendanceSummary).mock.calls
      expect(calls[calls.length - 1][1]).toEqual({ dateFrom: '2026-09-01', dateTo: '2026-09-30' })
    })
    // The filter change issued exactly ONE additional request.
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(2)
    await user.click(screen.getByRole('button', { name: 'Reset filter' }))
    await vi.waitFor(() => {
      const calls = vi.mocked(getMyAttendanceSummary).mock.calls
      expect(calls[calls.length - 1][1]).toEqual({})
    })
  })

  it('names the records table and exposes meaningful column headers', async () => {
    render(<AttendanceDetailPage />)
    const table = await screen.findByRole('table', { name: 'Your attendance records' })
    expect(within(table).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      'Date', 'Status', 'Notes',
    ])
  })

  it('renders backend statuses verbatim without inventing semantics', async () => {
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      summary: {
        ...NO_RECORDS.summary, records_available: true, total_classes: 1,
        excused_classes: 1,
      },
      records: [{ date: '2026-09-02', status: 'excused_leave', notes: null }],
    })
    render(<AttendanceDetailPage />)
    const table = await screen.findByRole('table', { name: 'Your attendance records' })
    expect(within(table).getByText('Excused leave')).toBeInTheDocument()
  })

  it('renders long notes and keeps the table horizontally scrollable', async () => {
    const longNote = 'Extended laboratory session with an unusually long descriptive note '.repeat(3).trim()
    vi.mocked(getMyAttendanceSummary).mockResolvedValue({
      summary: {
        ...NO_RECORDS.summary, records_available: true, total_classes: 1,
        present_classes: 1, attendance_percentage: 100,
      },
      records: [{ date: '2026-09-03', status: 'present', notes: longNote }],
    })
    render(<AttendanceDetailPage />)
    expect(await screen.findByText(longNote)).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Your attendance records' })
    expect(table.parentElement?.className).toContain('overflow-x-auto')
    expect(table.className).toContain('min-w-')
  })

  it('lays the summary out responsively without page-level overflow', async () => {
    const { container } = render(<AttendanceDetailPage />)
    await screen.findByText('80%')
    const summaryList = screen.getByText('Overall attendance').closest('dl')
    expect(summaryList?.className).toContain('grid-cols-2')
    expect(summaryList?.className).toContain('sm:grid-cols-4')
    expect(container.firstElementChild?.className).toContain('overflow-x-clip')
  })

  it('renders only student-safe attendance fields (no internal identifiers)', async () => {
    const withInternals = {
      summary: {
        records_available: true, total_classes: 1, present_classes: 1,
        absent_classes: 0, late_classes: 0, excused_classes: 0,
        attendance_percentage: 100,
      },
      records: [{
        date: '2026-09-05', status: 'present', notes: 'On time',
        attendance_id: 'att-11111111', student_id: 'stu-33333333',
        institution_id: 'inst-55555555', marked_by: 'usr-77777777',
      }],
    } as unknown as StudentOwnAttendance
    vi.mocked(getMyAttendanceSummary).mockResolvedValue(withInternals)
    render(<AttendanceDetailPage />)
    expect(await screen.findByText('On time')).toBeInTheDocument()
    expect(screen.queryByText(/11111111|33333333|55555555|77777777/)).toBeNull()
  })

  it('exposes no mutation control anywhere on the page', async () => {
    const { container } = render(<AttendanceDetailPage />)
    await screen.findByText('80%')
    const buttons = screen.getAllByRole('button').map((button) => button.textContent?.trim())
    expect(buttons).toEqual(['Apply date filter', 'Reset filter'])
    const inputs = Array.from(container.querySelectorAll('input'))
    expect(inputs).toHaveLength(2)
    expect(inputs.every((input) => input.type === 'date')).toBe(true)
    expect(container.querySelectorAll('textarea, select')).toHaveLength(0)
    expect(screen.getAllByRole('form')).toHaveLength(1)
  })
})

describe('attendance detail empty state', () => {
  it('uses neutral wording for a student with no records', async () => {
    vi.mocked(getMyAttendanceSummary).mockResolvedValue(NO_RECORDS)
    render(<AttendanceDetailPage />)
    expect(await screen.findByText('No attendance records are available yet.')).toBeInTheDocument()
  })

  it('never implies zero attendance from an empty response', async () => {
    vi.mocked(getMyAttendanceSummary).mockResolvedValue(NO_RECORDS)
    render(<AttendanceDetailPage />)
    await screen.findByText('No attendance records are available yet.')
    expect(screen.queryByText('0%')).toBeNull()
    expect(screen.queryByText('0')).toBeNull()
    expect(screen.queryByText('Absent')).toBeNull()
    expect(screen.queryByText(/fail/i)).toBeNull()
  })

  it('distinguishes an empty selection from a student with no records', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyAttendanceSummary)
      .mockResolvedValueOnce(ATTENDANCE)
      .mockResolvedValueOnce(NO_RECORDS)
    render(<AttendanceDetailPage />)
    await screen.findByText('80%')
    await user.type(screen.getByLabelText('From date'), '2027-01-01')
    await user.click(screen.getByRole('button', { name: 'Apply date filter' }))
    expect(
      await screen.findByText('No attendance records are available for this selection.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('No attendance records are available yet.')).toBeNull()
  })
})

describe('attendance detail loading, error and retry', () => {
  it('announces loading before the records arrive', async () => {
    let resolveRequest: (value: StudentOwnAttendance) => void = () => {}
    vi.mocked(getMyAttendanceSummary).mockReturnValue(
      new Promise<StudentOwnAttendance>((resolve) => { resolveRequest = resolve }),
    )
    render(<AttendanceDetailPage />)
    const statuses = await screen.findAllByRole('status')
    expect(statuses.some((node) => node.textContent?.includes('Loading your attendance'))).toBe(true)
    resolveRequest(ATTENDANCE)
    expect(await screen.findByText('80%')).toBeInTheDocument()
  })

  it('shows an error, retries only attendance, and keeps the session', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyAttendanceSummary)
      .mockRejectedValueOnce(new StudentApiError(500, 'Server error', undefined, 'INTERNAL_ERROR'))
      .mockResolvedValueOnce(ATTENDANCE)
    render(<AttendanceDetailPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load attendance.')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('80%')).toBeInTheDocument()
    expect(vi.mocked(getMyAttendanceSummary)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(getMyAcademicProfile)).toHaveBeenCalledTimes(1)
    expect(logoutMock).not.toHaveBeenCalled()
  })

  it('surfaces a backend filter rejection without ending the session', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyAttendanceSummary)
      .mockResolvedValueOnce(ATTENDANCE)
      .mockRejectedValueOnce(
        new StudentApiError(422, 'Invalid date filter.', undefined, 'INVALID_FILTER'),
      )
    render(<AttendanceDetailPage />)
    await screen.findByText('80%')
    await user.type(screen.getByLabelText('From date'), '2026-09-01')
    await user.click(screen.getByRole('button', { name: 'Apply date filter' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load attendance.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
    expect(logoutMock).not.toHaveBeenCalled()
  })

  it('surfaces a 401 as a retryable section error plus the global session event', async () => {
    vi.mocked(getMyAttendanceSummary).mockRejectedValue(
      new StudentApiError(401, 'Session expired.', undefined, 'UNAUTHORIZED'),
    )
    render(<AttendanceDetailPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load attendance.')
    // The page itself never signs the student out; the existing session-expiry
    // event (raised inside the API client) owns that transition.
    expect(logoutMock).not.toHaveBeenCalled()
  })
})

import { beforeEach, vi } from 'vitest'
import { getMyAcademicProfile, getMyAttendanceSummary } from '../../../../services/students/studentApi.ts'
import type { StudentOwnAttendance } from '../../../../types/student.ts'
import { ATTENDANCE, PROFILE } from '../../__tests__/studentTestFixtures.ts'
const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))

/** What a brand-new approved student legitimately receives: no records at all. */
export const NO_RECORDS: StudentOwnAttendance = {
  summary: {
    records_available: false,
    total_classes: 0,
    present_classes: 0,
    absent_classes: 0,
    late_classes: 0,
    excused_classes: 0,
    attendance_percentage: null,
  },
  records: [],
}

vi.mock('../../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' },
    role: 'student',
    accessToken: 'test-token',
    logout: logoutMock,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('../../../../services/students/studentApi.ts', () => ({
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

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
  vi.mocked(getMyAttendanceSummary).mockResolvedValue(ATTENDANCE)
})

export { logoutMock }

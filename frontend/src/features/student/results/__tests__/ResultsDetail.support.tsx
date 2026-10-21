import { beforeEach, vi } from 'vitest'
import { getMyAcademicProfile, getMyResultsSummary, getMyTestResultsSummary } from '../../../../services/students/studentApi.ts'
import type { StudentOwnResults, StudentOwnTestResults } from '../../../../types/student.ts'
import { PROFILE, RESULTS, TEST_RESULTS } from '../../__tests__/studentTestFixtures.ts'
const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))

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

/** A newly approved student: no published results of either category yet. */
export const NO_RESULTS: StudentOwnResults = {
  summary: { records_available: false, total_results: 0 },
  records: [],
}

export const NO_TEST_RESULTS: StudentOwnTestResults = {
  summary: { records_available: false, total_results: 0 },
  records: [],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
  vi.mocked(getMyResultsSummary).mockResolvedValue(RESULTS)
  vi.mocked(getMyTestResultsSummary).mockResolvedValue(TEST_RESULTS)
})

export { logoutMock }

import { beforeEach, vi } from 'vitest'
import {
  commitFacultyAttendanceImport,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceImports,
  getFacultyAttendanceOverview,
  getFacultyAttendanceProfile,
  getFacultyAttendanceRoster,
  getFacultyAttendanceSessions,
  getFacultyAttendanceStudents,
  markFacultyAttendance,
  uploadFacultyAttendance,
} from '../../../../services/faculty/facultyAttendanceApi.ts'
vi.mock('../../../../services/faculty/facultyAttendanceApi.ts', () => ({
  commitFacultyAttendanceImport: vi.fn(),
  getFacultyAttendanceAssignments: vi.fn(),
  getFacultyAttendanceRoster: vi.fn(),
  markFacultyAttendance: vi.fn(),
  uploadFacultyAttendance: vi.fn(),
  getFacultyAttendanceStudents: vi.fn(),
  getFacultyAttendanceOverview: vi.fn(),
  getFacultyAttendanceProfile: vi.fn(),
  getFacultyAttendanceImports: vi.fn(),
  getFacultyAttendanceSessions: vi.fn(),
  getFacultyAttendanceImportReview: vi.fn(),
  correctFacultyAttendanceImportRow: vi.fn(),
}))

export const assignment = {
  assignment_id: 'assignment-1',
  assigned_at: '2026-10-06T00:00:00Z',
  section_id: 'section-1',
  semester_id: 'semester-1',
  academic_year_id: 'year-1',
  can_manage: true,
  section: {
    section_id: 'section-1',
    name: 'Section A',
    code: 'A',
    course: { name: 'Data Mining', code: 'CS-501' },
    department_id: 'dept-1',
    department: { department_id: 'dept-1', name: 'Computing' },
    program_id: 'program-1',
    program: { program_id: 'program-1', name: 'B.Tech' },
    academic_year_id: 'year-1',
    academic_year: { academic_year_id: 'year-1', name: '2026–27' },
    semester_id: 'semester-1',
    semester: { semester_id: 'semester-1', name: 'Semester 1' },
  },
}

export const roster = [
  {
    roster_id: 'roster-1',
    register_number: 'CSE23-001',
    university_roll_number: '2023CSE001',
    student_name: 'Rahul Sharma',
    email: 'rahul@example.com',
    address: null,
    roster_status: 'ACTIVE' as const,
    linked_student_id: 'student-1',
    attendance_percentage: 92.86,
    record_count: 28,
    present: 26,
    absent: 2,
    imported_summary: { attendance_percentage: 1, total_classes: 200 },
  },
]

export const overview = {
  total_students: 1,
  session_count: 28,
  present: 26,
  absent: 2,
  average_attendance: 92.86,
  low_attendance_count: 0,
  monitoring_threshold: 75,
  trend: [],
}

export function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment])
  vi.mocked(getFacultyAttendanceRoster).mockResolvedValue(roster)
  vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: roster, total: 1 })
  vi.mocked(getFacultyAttendanceOverview).mockResolvedValue(overview)
  vi.mocked(getFacultyAttendanceImports).mockResolvedValue([])
  vi.mocked(getFacultyAttendanceSessions).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(getFacultyAttendanceProfile).mockResolvedValue({
    student: roster[0],
    section: assignment.section,
    total: 1,
    history: [{ record_id: 'record-1', session_date: '2026-10-07', status: 'present' }],
  })
  vi.mocked(markFacultyAttendance).mockResolvedValue({ session_id: 'session-1', record_count: 1 })
  vi.mocked(uploadFacultyAttendance).mockResolvedValue({
    import_id: 'import-1',
    summary: { total_rows: 1, valid: 1, new_records: 1, updates: 0, errors: 0 },
    rows: [{ row_number: 2, normalized_data: { student_name: 'Rahul Sharma' }, validation_status: 'NEW', errors: [] }],
  })
  vi.mocked(commitFacultyAttendanceImport).mockResolvedValue({ imported_rows: 1 })
})

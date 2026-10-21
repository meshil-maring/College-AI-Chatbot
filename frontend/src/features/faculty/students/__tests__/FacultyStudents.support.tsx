import { beforeEach, vi } from 'vitest'
import {
  getFacultyAttendanceAssignments,
  getFacultyAttendanceProfile,
  getFacultyAttendanceStudents,
  getFacultyStudentRegistrationHistory,
  type FacultyAttendanceRosterRow,
} from '../../../../services/faculty/facultyAttendanceApi.ts'
import {
  getClassStudentRegistrations,
  getRegistrationBatches,
  type ClassStudentRegistration,
} from '../../../../services/students/studentRegistrationApi.ts'
vi.mock('../../../../services/students/studentRegistrationApi.ts', () => ({
  createClassStudentRegistration: vi.fn(),
  getClassStudentRegistrations: vi.fn(),
  getRegistrationBatches: vi.fn(),
}))

vi.mock('../../../../services/faculty/facultyAttendanceApi.ts', () => ({
  getFacultyAttendanceAssignments: vi.fn(),
  getFacultyAttendanceProfile: vi.fn(),
  getFacultyAttendanceStudents: vi.fn(),
  getFacultyStudentRegistrationHistory: vi.fn(),
}))

export const assignment = {
  can_manage: true,
  assignment_id: 'section-1',
  assigned_at: '',
  section_id: 'section-1',
  semester_id: 'semester-1',
  academic_year_id: 'year-1',
  section: {
    section_id: 'section-1',
    name: 'Section A',
    code: 'A',
    program_id: 'program-1',
    program: { program_id: 'program-1', name: 'Computer Science', degree_type: 'B.Tech' },
    course: { name: 'Data Mining', code: 'CS501' },
  },
}

export const student: FacultyAttendanceRosterRow & ClassStudentRegistration = {
  registration_id: 'registration-1',
  batch_id: 'batch-1',
  program_id: 'program-1',
  section_code: 'A',
  batch_start_year: 2026,
  batch_end_year: 2030,
  identity_conflict: false,
  subjects_assigned: false,
  roster_id: 'roster-1',
  student_name: 'Ada Rao',
  register_number: 'CS001',
  university_roll_number: 'UNI001',
  email: 'ada@college.edu',
  roster_status: 'ACTIVE',
  linked_student_id: 'student-1',
  attendance_percentage: 80,
}

beforeEach(() => {
  window.history.replaceState(null, '', '/faculty/students')
  vi.resetAllMocks()
  vi.mocked(getRegistrationBatches).mockResolvedValue([
    { batch_id: 'batch-1', program_id: 'program-1', start_year: 2026, end_year: 2030, is_active: true },
  ])
  vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment])
  vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 1 })
  vi.mocked(getFacultyAttendanceProfile).mockResolvedValue({
    student,
    section: assignment.section,
    total: 1,
    history: [{ record_id: 'record-1', session_date: '2026-10-15', status: 'present' }],
  })
  vi.mocked(getFacultyStudentRegistrationHistory).mockResolvedValue({ items: [], total: 0 })
})

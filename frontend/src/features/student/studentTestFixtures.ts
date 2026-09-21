/** Phase 6.16 — shared fixtures for student experience tests. */
import { vi } from 'vitest'
import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../services/studentApi.ts'

export const PROFILE = {
  student_number: 'STU100',
  register_number: 'REG-100',
  university_roll_number: 'ROLL-100',
  email: 'student@college.edu',
  institution_name: 'Test College',
  institution_code: 'TC01',
  program_name: 'B.Tech CSE',
  program_code: 'CSE',
  academic_year_name: '2024-25',
  academic_year_code: 'AY24',
  current_semester_name: 'Semester 3',
  current_semester_code: 'S3',
  approval_status: 'approved',
  status: 'active',
}
export const ATTENDANCE = {
  summary: {
    records_available: true, total_classes: 10, present_classes: 8,
    absent_classes: 2, late_classes: 0, excused_classes: 0,
    attendance_percentage: 80,
  },
  records: [{ date: '2026-09-01', status: 'present', notes: null }],
}
export const RESULTS = {
  summary: { records_available: true, total_results: 1 },
  records: [{
    result_type: 'semester', total_credits_earned: 20,
    total_credits_max: 22, sgpa: 8.5, cgpa: 8.2,
    status: 'pass', issued_at: '2026-08-01',
  }],
}
export const TEST_RESULTS = {
  summary: { records_available: true, total_results: 1 },
  records: [{
    test_name: 'Midterm 1', test_type: 'internal', course_code: 'CS301',
    course_name: 'Databases', max_marks: 50, scored_marks: 42,
    percentage: 84, letter_grade: 'A', conducted_at: '2026-07-15',
  }],
}
export const NOTICES = {
  items: [{
    notice_id: 'notice-1', title: 'Exam schedule update',
    content: 'Exams begin Monday.', category: 'exam', priority: 'high',
    is_pinned: true, published_at: '2026-09-01T00:00:00Z', expires_at: null,
  }],
  total: 1,
}
export const RESOURCES = {
  items: [{
    resource_id: 'resource-1', title: 'Lecture notes week 3',
    description: 'Study material', source_type: 'document',
    effective_from: '2026-09-01T00:00:00Z', effective_until: null,
  }],
  total: 1,
}
export function mockAllLoaded() {
  vi.mocked(getMyAcademicProfile).mockResolvedValue(PROFILE)
  vi.mocked(getMyAttendanceSummary).mockResolvedValue(ATTENDANCE)
  vi.mocked(getMyResultsSummary).mockResolvedValue(RESULTS)
  vi.mocked(getMyTestResultsSummary).mockResolvedValue(TEST_RESULTS)
  vi.mocked(getMyNotices).mockResolvedValue(NOTICES)
  vi.mocked(getMyResources).mockResolvedValue(RESOURCES)
}

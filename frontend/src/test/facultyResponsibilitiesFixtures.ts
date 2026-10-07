import type { FacultyContext, FacultyResponsibility, ResponsibilityManagement, ResponsibilityReport } from '../types/faculty.ts'

export const hodResponsibility: FacultyResponsibility = {
  responsibility_id: 'hod-1', faculty_user_id: 'faculty-1', responsibility_code: 'hod', name: 'HOD',
  scope_type: 'department', scope_id: 'department-1', scope_label: 'CSE Department', state: 'active',
  start_at: '2000-01-01T00:00:00Z', end_at: null, is_active: true, revoked_at: null, effective_active: true,
  permissions: ['academic.department.read', 'academic.reports.read', 'attendance.overview.read', 'students.read', 'faculty.read'],
}
export const classResponsibility: FacultyResponsibility = {
  ...hodResponsibility, responsibility_id: 'class-1', responsibility_code: 'class_in_charge', name: 'Class In-Charge',
  scope_type: 'section', scope_id: 'section-1', scope_label: 'B.Tech CSE · Semester 5 · Section A',
  permissions: ['academic.class.read', 'academic.reports.read', 'attendance.overview.read', 'students.read'],
}
export const academicSection = {
  section_id: 'section-1', code: 'A', name: 'Section A', course: { code: 'DM', name: 'Data Mining' },
  program: { name: 'B.Tech CSE' }, semester: { name: 'Semester 5' }, academic_year: { name: '2026–27' },
}
export const facultyContextFixture: FacultyContext = {
  responsibilities: [hodResponsibility, classResponsibility],
  teaching_assignments: [{ assignment_id: 'teaching-1', faculty_user_id: 'faculty-1', section_id: 'section-1', assigned_at: '2000-01-01T00:00:00Z', start_at: '2000-01-01T00:00:00Z', end_at: null, is_active: true, section: academicSection }],
  responsibility_permissions: [...hodResponsibility.permissions, ...classResponsibility.permissions],
}
export const responsibilityManagementFixture: ResponsibilityManagement = {
  faculty: [{ id: 'faculty-1', first_name: 'Ada', last_name: 'Lovelace', email: 'ada@example.test' }],
  departments: [{ department_id: 'department-1', name: 'CSE Department', code: 'CSE' }],
  sections: [academicSection], responsibilities: [hodResponsibility, classResponsibility],
  definitions: [{ code: 'hod', name: 'HOD', allowed_scope_types: ['department'], exclusive_scope: true, permissions: hodResponsibility.permissions }, { code: 'class_in_charge', name: 'Class In-Charge', allowed_scope_types: ['section'], exclusive_scope: true, permissions: classResponsibility.permissions }],
}
export const responsibilityReportFixture: ResponsibilityReport = {
  responsibility: hodResponsibility, sections: [academicSection], faculty: [{ id: 'faculty-1', first_name: 'Ada', last_name: 'Lovelace' }],
  students: [{ roster_id: 'roster-1', section_id: 'section-1', register_number: 'R-1', student_name: 'Student One', roster_status: 'ACTIVE', total_classes: 10, present_classes: 7, attendance_percentage: 70 }],
  low_attendance: [{ roster_id: 'roster-1', section_id: 'section-1', register_number: 'R-1', student_name: 'Student One', roster_status: 'ACTIVE', total_classes: 10, present_classes: 7, attendance_percentage: 70 }],
  low_attendance_threshold: 75, session_count: 10,
}

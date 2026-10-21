import { getFacultyAttendanceAssignments, getFacultyAttendanceProfile, getFacultyAttendanceStudents, getFacultyStudentRegistrationHistory } from '../faculty/facultyAttendanceApi.ts'
import { createClassStudentRegistration, getClassStudentRegistrations, getRegistrationBatches, sendStudentRegistrationInvitation } from './studentRegistrationApi.ts'

export interface StudentWorkspaceApi {
  namespace: 'faculty' | 'admin'
  getSections: typeof getFacultyAttendanceAssignments
  getStudents: typeof getFacultyAttendanceStudents
  getProfile: typeof getFacultyAttendanceProfile
  getHistory: typeof getFacultyStudentRegistrationHistory
  getRegistrations: typeof getClassStudentRegistrations
  createRegistration: typeof createClassStudentRegistration
  getBatches: typeof getRegistrationBatches
  sendInvitation: typeof sendStudentRegistrationInvitation
}

export const facultyStudentWorkspaceApi: StudentWorkspaceApi = {
  namespace: 'faculty',
  getSections: (...args) => getFacultyAttendanceAssignments(...args),
  getStudents: (...args) => getFacultyAttendanceStudents(...args),
  getProfile: (...args) => getFacultyAttendanceProfile(...args),
  getHistory: (...args) => getFacultyStudentRegistrationHistory(...args),
  getRegistrations: (...args) => getClassStudentRegistrations(...args),
  createRegistration: (...args) => createClassStudentRegistration(...args),
  getBatches: (...args) => getRegistrationBatches(...args),
  sendInvitation: (...args) => sendStudentRegistrationInvitation(...args),
}

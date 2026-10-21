export type AttendanceValue = 'present' | 'absent' | 'late' | 'excused'

export type UploadStep = 1 | 2 | 3 | 4

export type AttendanceTab = 'students' | 'history' | 'sessions' | 'reports'

export type ImportedStats = {
  percentage: number | null
  present: number | null
  absent: number | null
  classes: number | null
}

export type AttendanceActionRequest = { action: 'overview' | 'students' | 'mark' | 'upload' | 'history'; id: number }

export type FacultyAttendanceProps = {
  accessToken: string
  actionRequest?: AttendanceActionRequest
  onNavigateAssignments?: () => void
  scopeVersion?: string
}

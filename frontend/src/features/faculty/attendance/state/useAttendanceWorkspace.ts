import { createAttendanceActions } from './createAttendanceActions.ts'
import { useAttendanceState } from './useAttendanceState.ts'

export function useAttendanceWorkspace(props: Parameters<typeof useAttendanceState>[0]) {
  const state = useAttendanceState(props)
  return { ...state, ...createAttendanceActions(state) }
}

export type FacultyAttendanceWorkspaceModel = ReturnType<typeof useAttendanceWorkspace>

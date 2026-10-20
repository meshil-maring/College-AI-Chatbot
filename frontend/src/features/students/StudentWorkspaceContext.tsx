import { createContext, useContext } from 'react'
import { facultyStudentWorkspaceApi } from '../../services/studentWorkspaceApi.ts'

export const StudentWorkspaceContext = createContext(facultyStudentWorkspaceApi)
export const useStudentWorkspaceApi = () => useContext(StudentWorkspaceContext)

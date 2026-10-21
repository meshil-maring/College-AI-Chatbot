import { createContext, useContext } from 'react'
import { facultyStudentWorkspaceApi } from '../../services/students/studentWorkspaceApi.ts'

export const StudentWorkspaceContext = createContext(facultyStudentWorkspaceApi)
export const useStudentWorkspaceApi = () => useContext(StudentWorkspaceContext)

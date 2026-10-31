import type {
  AcademicCatalogue,
  AcademicCreateMap,
  AcademicEntity,
  AcademicRecordMap,
  AcademicUpdateMap,
  Department,
  DegreeProgram,
  AcademicYear,
  Semester,
} from '../../types/academicSetup.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

const BASE = `${ADMIN_BASE}/academic-setup`

export function getAcademicSetup(accessToken: string): Promise<AcademicCatalogue> {
  return requestJson('GET', BASE, accessToken)
}

export function createAcademicRecord<E extends AcademicEntity>(
  accessToken: string,
  entity: E,
  payload: AcademicCreateMap[E],
): Promise<AcademicRecordMap[E]> {
  return requestJson('POST', `${BASE}/${entity}`, accessToken, payload)
}

export function updateAcademicRecord<E extends AcademicEntity>(
  accessToken: string,
  entity: E,
  id: string,
  payload: AcademicUpdateMap[E],
): Promise<AcademicRecordMap[E]> {
  return requestJson('PATCH', `${BASE}/${entity}/${encodeURIComponent(id)}`, accessToken, payload)
}

export function deleteDepartment(accessToken: string, id: string): Promise<Department> {
  return requestJson('DELETE', `${BASE}/departments/${encodeURIComponent(id)}`, accessToken)
}

export function deleteProgram(accessToken: string, id: string): Promise<DegreeProgram> {
  return requestJson('DELETE', `${BASE}/programs/${encodeURIComponent(id)}`, accessToken)
}

export function deleteAcademicYear(accessToken: string, id: string): Promise<AcademicYear> {
  return requestJson('DELETE', `${BASE}/academic_years/${encodeURIComponent(id)}`, accessToken)
}

export function deleteSemester(accessToken: string, id: string): Promise<Semester> {
  return requestJson('DELETE', `${BASE}/semesters/${encodeURIComponent(id)}`, accessToken)
}

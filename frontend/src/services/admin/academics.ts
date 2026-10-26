import type {
  AcademicCatalogue,
  AcademicCreateMap,
  AcademicEntity,
  AcademicRecordMap,
  AcademicUpdateMap,
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

import type { AcademicCatalogue, AcademicEntity, AcademicRecord } from '../../types/academicSetup.ts'
import { ADMIN_BASE, requestJson } from './http.ts'
export function getAcademicCatalogue(accessToken: string): Promise<AcademicCatalogue> {
  return requestJson('GET', `${ADMIN_BASE}/academic-setup`, accessToken)
}

export function saveAcademicRecord(
  accessToken: string,
  entity: AcademicEntity,
  payload: AcademicRecord,
  id?: string,
): Promise<AcademicRecord> {
  return requestJson(
    id ? 'PATCH' : 'POST',
    `${ADMIN_BASE}/academic-setup/${entity}${id ? `/${encodeURIComponent(id)}` : ''}`,
    accessToken,
    payload,
  )
}

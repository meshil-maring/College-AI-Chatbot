import type {
  StructureCatalogue,
  StructureCreateMap,
  StructureEntity,
  StructureRecordMap,
  StructureUpdateMap,
} from '../../types/academicStructure.ts'
import { ADMIN_BASE, requestJson } from './http.ts'

const BASE = `${ADMIN_BASE}/academic-structure`

export function getAcademicStructure(accessToken: string): Promise<StructureCatalogue> {
  return requestJson('GET', BASE, accessToken)
}
export function createStructureRecord<E extends StructureEntity>(
  accessToken: string,
  entity: E,
  payload: StructureCreateMap[E],
): Promise<StructureRecordMap[E]> {
  return requestJson('POST', `${BASE}/${entity}`, accessToken, payload)
}
export function updateStructureRecord<E extends StructureEntity>(
  accessToken: string,
  entity: E,
  id: string,
  payload: StructureUpdateMap[E],
): Promise<StructureRecordMap[E]> {
  return requestJson('PATCH', `${BASE}/${entity}/${encodeURIComponent(id)}`, accessToken, payload)
}

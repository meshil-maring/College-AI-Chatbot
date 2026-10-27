import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { getAcademicSetup } from '../../../../services/admin/academics.ts'
import type { AcademicCatalogue, AcademicEntity } from '../../../../types/academicSetup.ts'
import { getAcademicArea, summaryPages } from './academicOverviewModel.ts'
import { hasPermission } from '../../../auth/access/permissions.ts'

export function hasAcademicCatalogueReadAccess(permissions: readonly string[] | undefined) {
  return ['departments.read', 'academic_years.read', 'semesters.read', 'courses.read'].some((permission) =>
    hasPermission(permissions, permission),
  )
}

export function useAcademicOverview(
  accessToken: string,
  identity: string,
  institutionId: string,
  canReadCatalogues: boolean,
) {
  const query = useApiQuery(
    ['admin', 'academic-overview', identity],
    () => getAcademicSetup(accessToken),
    canReadCatalogues,
  )
  const catalogue = canReadCatalogues && query.data?.institution_id === institutionId ? query.data : undefined
  const error = !canReadCatalogues
    ? undefined
    : query.isError
      ? 'Academic data could not be loaded. Retry to refresh counts and available actions.'
      : query.data && !catalogue
        ? 'Academic data is unavailable for this institution.'
        : undefined
  return { query, catalogue, error, loading: canReadCatalogues && query.isPending }
}

export function overviewRecords(catalogue: AcademicCatalogue | undefined, entity: AcademicEntity | undefined) {
  if (!entity || !catalogue) return undefined
  return catalogue.records[entity]?.filter((record) => record.institution_id === catalogue.institution_id)
}

export function searchAcademicRecords(catalogue: AcademicCatalogue | undefined, search: string) {
  return summaryPages.flatMap((page) => {
    const area = getAcademicArea(page)!
    const entity = area.entity!
    return (overviewRecords(catalogue, entity) ?? []).flatMap((record) =>
      'name' in record && `${record.name} ${record.code}`.toLowerCase().includes(search)
        ? [{ entity, title: area.title, name: record.name, code: record.code }]
        : [],
    )
  })
}

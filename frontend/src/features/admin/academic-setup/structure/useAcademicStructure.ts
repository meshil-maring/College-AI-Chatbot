import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { getAcademicStructure } from '../../../../services/admin/academicStructure.ts'
import { AdminApiError } from '../../../../services/admin/http.ts'
import type { StructureCatalogue, StructureEntity } from '../../../../types/academicStructure.ts'
import { useAcademicOverview } from '../overview/useAcademicOverview.ts'

export interface StructureContext {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
}
export function useAcademicStructure(context: StructureContext) {
  const base = useAcademicOverview(
    context.accessToken,
    context.identity,
    context.institutionId,
    context.canReadCatalogues,
  )
  const query = useApiQuery(
    ['admin', 'academic-structure', context.identity],
    () => getAcademicStructure(context.accessToken),
    context.canReadCatalogues,
    { cache: 'navigation' },
  )
  const denied = query.error instanceof AdminApiError && [401, 403].includes(query.error.status)
  const valid = context.canReadCatalogues && query.data?.institution_id === context.institutionId && !denied
  const structure: StructureCatalogue | undefined = valid
    ? {
        ...query.data!,
        records: Object.fromEntries(
          Object.entries(query.data!.records).map(([entity, records]) => [
            entity,
            records.filter((record) => record.institution_id === context.institutionId),
          ]),
        ) as StructureCatalogue['records'],
      }
    : undefined
  const baseDenied = base.query.error instanceof AdminApiError && [401, 403].includes(base.query.error.status)
  const catalogue = baseDenied ? undefined : base.catalogue
  const error =
    base.error ??
    (query.error instanceof Error
      ? query.error.message
      : query.isError
        ? 'Academic structure could not be loaded.'
        : query.data && !valid
          ? 'Academic data is unavailable for this institution.'
          : undefined)
  const busy = base.query.isFetching || query.isFetching || Boolean(error)
  function canManage(entity: StructureEntity) {
    return !busy && Boolean(structure?.records[entity] && structure.manageable.includes(entity))
  }
  return {
    context,
    query: base.query,
    structureQuery: query,
    catalogue,
    structure,
    error,
    busy,
    refreshing: base.query.isFetching || query.isFetching,
    denied: denied || baseDenied,
    loading: context.canReadCatalogues && (base.loading || query.isPending),
    canManage,
    refresh: () => Promise.all([base.query.refetch(), query.refetch()]),
  }
}
export type AcademicStructureState = ReturnType<typeof useAcademicStructure>

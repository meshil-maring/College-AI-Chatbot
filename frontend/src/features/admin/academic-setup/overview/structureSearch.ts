import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'
import { allAcademicAreas } from './academicOverviewModel.ts'

export function searchStructureRecords(
  catalogue: AcademicCatalogue | undefined,
  structure: StructureCatalogue | undefined,
  search: string,
) {
  if (!structure || (catalogue && catalogue.institution_id !== structure.institution_id)) return []
  const tenant = structure.institution_id
  return allAcademicAreas.flatMap((area) => {
    const entity = area.structureEntity
    if (!entity) return []
    return (structure.records[entity] ?? []).flatMap((record) => {
      if (record.institution_id !== tenant) return []
      const course =
        'course_id' in record
          ? catalogue?.records.courses?.find(
              (item) => item.institution_id === tenant && item.course_id === record.course_id,
            )
          : undefined
      const name = 'name' in record ? record.name : course?.name
      const code = 'code' in record ? record.code : 'version' in record ? record.version : (course?.code ?? '')
      return name && `${name} ${code}`.toLowerCase().includes(search)
        ? [{ entity, title: area.title, name, code, destination: area.page }]
        : []
    })
  })
}

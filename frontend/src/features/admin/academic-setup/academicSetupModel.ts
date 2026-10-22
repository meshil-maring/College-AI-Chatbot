import type { AcademicCatalogue, AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'
import { ACADEMIC_DEFINITIONS } from './academicSetupDefinitions.ts'

export function records(data: AcademicCatalogue, entity: AcademicEntity): AcademicRecord[] {
  return data.records[entity] ?? []
}
export function find(data: AcademicCatalogue, entity: AcademicEntity, id: unknown) {
  return records(data, entity).find((row) => row[ACADEMIC_DEFINITIONS[entity].id] === id)
}
export function usable(data: AcademicCatalogue, entity: AcademicEntity, row: AcademicRecord): boolean {
  if (!row.is_active) return false
  const ancestry: Partial<Record<AcademicEntity, [AcademicEntity, string][]>> = {
    programs: [['departments', 'department_id']],
    courses: [['departments', 'department_id']],
    batches: [['programs', 'program_id']],
    semesters: [['academic_years', 'academic_year_id']],
    program_courses: [
      ['programs', 'program_id'],
      ['courses', 'course_id'],
      ...(row.semester_id ? [['semesters', 'semester_id'] as [AcademicEntity, string]] : []),
    ],
    course_offerings: [
      ['programs', 'program_id'],
      ['courses', 'course_id'],
      ['academic_years', 'academic_year_id'],
      ['semesters', 'semester_id'],
    ],
    sections: [['course_offerings', 'course_offering_id']],
  }
  return (ancestry[entity] ?? []).every(([source, key]) => {
    const value = find(data, source, row[key])
    return value !== undefined && usable(data, source, value)
  })
}
export function missingPrerequisites(data: AcademicCatalogue, entity: AcademicEntity): AcademicEntity[] {
  return ACADEMIC_DEFINITIONS[entity].requires.filter(
    (source) =>
      !(entity === 'course_offerings' && source === 'program_courses' && namedOfferingEligibility(data).length) &&
      !records(data, source).some((row) => usable(data, source, row)),
  )
}
export function namedOfferingEligibility(data: AcademicCatalogue) {
  return (data.offering_eligibility ?? []).filter((entry) =>
    (
      [
        ['programs', entry.program_id],
        ['courses', entry.course_id],
        ['semesters', entry.semester_id],
      ] as const
    ).every(([entity, id]) => {
      const row = find(data, entity, id)
      return row !== undefined && usable(data, entity, row)
    }),
  )
}
export function offeringSubjectEligible(
  data: AcademicCatalogue,
  programId: unknown,
  courseId: unknown,
  semesterId: unknown,
) {
  return (
    records(data, 'program_courses').some(
      (link) =>
        usable(data, 'program_courses', link) &&
        link.program_id === programId &&
        link.course_id === courseId &&
        (!link.semester_id || link.semester_id === semesterId),
    ) ||
    namedOfferingEligibility(data).some(
      (entry) => entry.program_id === programId && entry.course_id === courseId && entry.semester_id === semesterId,
    )
  )
}
export function label(data: AcademicCatalogue, entity: AcademicEntity, row: AcademicRecord): string {
  if (entity === 'batches')
    return `${row.start_year}–${row.end_year} · ${find(data, 'programs', row.program_id)?.name ?? 'Branch unavailable'}`
  if (entity === 'course_offerings' || entity === 'program_courses') {
    const subject = find(data, 'courses', row.course_id),
      program = find(data, 'programs', row.program_id),
      term = find(data, 'semesters', row.semester_id)
    const year = find(data, 'academic_years', row.academic_year_id ?? term?.academic_year_id)
    return [program?.code, subject?.code, year?.name, term?.name].filter(Boolean).join(' · ')
  }
  if (entity === 'semesters')
    return `${find(data, 'academic_years', row.academic_year_id)?.name ?? ''} · ${row.code} · ${row.name}`
  if (entity === 'sections') {
    const offering = find(data, 'course_offerings', row.course_offering_id)
    return `${offering ? label(data, 'course_offerings', offering) : ''} · ${row.code} · ${row.name}`
  }
  return `${row.code} · ${row.name}`
}

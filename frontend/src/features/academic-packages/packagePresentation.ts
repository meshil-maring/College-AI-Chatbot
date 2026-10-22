import type {
  AcademicPackageCatalogue,
  PackageCollection,
  PackageOption,
  PackageRecord,
} from '../../types/academicPackages.ts'

export function value(row: PackageRecord | undefined, key: string): string {
  const item = row?.[key]
  return typeof item === 'string' || typeof item === 'number' ? String(item) : ''
}

export function canManage(data: AcademicPackageCatalogue, domain: 'curriculum' | 'class') {
  if (data.capabilities.includes(domain === 'curriculum' ? 'manage_curriculum' : 'manage_class')) return true
  const granular = data.capabilities.includes('manage_curriculum') || data.capabilities.includes('manage_class')
  return !granular && data.capabilities.includes('manage')
}

export const primaryKeys: Record<PackageCollection | PackageOption, string> = {
  curricula: 'curriculum_id',
  curriculum_subjects: 'curriculum_subject_id',
  packages: 'package_id',
  package_subjects: 'package_subject_id',
  classes: 'class_id',
  class_packages: 'class_package_id',
  class_subjects: 'class_subject_id',
  placements: 'placement_id',
  assignments: 'assignment_id',
  requests: 'request_id',
  history: 'history_id',
  programs: 'program_id',
  batches: 'batch_id',
  academic_years: 'academic_year_id',
  semesters: 'semester_id',
  subjects: 'course_id',
  sections: 'section_id',
  registrations: 'registration_id',
  class_responsibilities: 'class_responsibility_id',
  responsibilities: 'responsibility_id',
}

export function rows(data: AcademicPackageCatalogue, source: PackageCollection | PackageOption): PackageRecord[] {
  return (
    (data.records as Record<string, PackageRecord[] | undefined>)[source] ??
    (data.options as Record<string, PackageRecord[] | undefined>)[source] ??
    []
  )
}

export function find(data: AcademicPackageCatalogue, source: PackageCollection | PackageOption, id: string) {
  return rows(data, source).find((row) => value(row, primaryKeys[source]) === id)
}

export function label(
  data: AcademicPackageCatalogue,
  source: PackageCollection | PackageOption,
  row: PackageRecord,
): string {
  if (source === 'packages' && value(row, 'selection_code'))
    return `${value(row, 'selection_code')} · ${value(row, 'name')}`
  if (source === 'classes')
    return `${value(row, 'code') || value(row, 'section_code')} · ${labelForId(data, 'programs', value(row, 'program_id'))} · ${labelForId(data, 'batches', value(row, 'batch_id'))} · Study semester ${value(row, 'study_semester')}`
  if (source === 'semesters') {
    const year = find(data, 'academic_years', value(row, 'academic_year_id'))
    return `${value(row, 'name')} · ${value(year, 'name') || value(row, 'start_date')}`
  }
  if (source === 'curriculum_subjects') {
    const subject = find(data, 'subjects', value(row, 'course_id'))
    return `${value(subject, 'name') || value(subject, 'code') || 'Subject'} · Semester ${value(row, 'study_semester')} · ${row.is_core ? 'Shared core' : value(row, 'course_type')}`
  }
  if (source === 'placements') {
    const registration = find(data, 'registrations', value(row, 'registration_id'))
    return `${value(registration, 'student_name') || value(row, 'student_name') || 'Student'} · ${value(registration, 'register_number')} · ${labelForId(data, 'classes', value(row, 'class_id'))}`
  }
  if (source === 'assignments')
    return `${labelForId(data, 'placements', value(row, 'placement_id'))} · ${labelForId(data, 'packages', value(row, 'package_id'))}`
  if (source === 'batches') return `${value(row, 'start_year')}–${value(row, 'end_year')}`
  if (source === 'registrations') return `${value(row, 'student_name')} · ${value(row, 'register_number')}`
  if (source === 'sections')
    return `${value(row, 'subject_name') || value(row, 'course_name') || value(row, 'course_code')} · ${value(row, 'name') || value(row, 'code')}`
  if (source === 'responsibilities')
    return `${value(row, 'name')} · ${value(row, 'faculty_email')} · ${labelForId(data, 'programs', value(row, 'program_id'))} · ${labelForId(data, 'semesters', value(row, 'semester_id'))} · ${labelForId(data, 'sections', value(row, 'section_id'))}`
  const title = value(row, 'name') || value(row, 'code') || value(row, 'section_code') || value(row, 'status')
  return `${title || 'Record'}${value(row, 'name') && value(row, 'code') ? ` · ${value(row, 'code')}` : ''}${value(row, 'version') ? ` · v${value(row, 'version')}` : ''}`
}

export function labelForId(data: AcademicPackageCatalogue, source: PackageCollection | PackageOption, id: string) {
  const row = find(data, source, id)
  return row ? label(data, source, row) : 'Unavailable record'
}

export function classForAssignment(data: AcademicPackageCatalogue, assignment: PackageRecord) {
  const placement = find(data, 'placements', value(assignment, 'placement_id'))
  return find(data, 'classes', value(placement, 'class_id'))
}

export function isLocked(academicClass: PackageRecord | undefined, now = Date.now()) {
  if (!academicClass) return true
  const cutoff = Date.parse(value(academicClass, 'change_cutoff'))
  return academicClass.changes_locked === true || !Number.isFinite(cutoff) || now >= cutoff
}

export function formatDeadline(academicClass: PackageRecord | undefined) {
  const date = new Date(value(academicClass, 'change_cutoff'))
  return Number.isNaN(date.valueOf())
    ? 'Deadline unavailable'
    : `${date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' })} IST`
}

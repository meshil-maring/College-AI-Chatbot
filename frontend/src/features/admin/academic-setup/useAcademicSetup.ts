import { useEffect, useState, type FormEvent } from 'react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { getAcademicCatalogue, saveAcademicRecord } from '../../../services/admin/adminApi.ts'
import type { AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'
import {
  ACADEMIC_DEFINITIONS,
  ACADEMIC_ENTITIES as entities,
  type AcademicField as Field,
} from './academicSetupDefinitions.ts'
import {
  records,
  find,
  usable,
  missingPrerequisites,
  namedOfferingEligibility,
  offeringSubjectEligible,
} from './academicSetupModel.ts'
import {
  adminAcademicKeys,
  invalidateAcademicPackageOptions,
  invalidateFacultyAcademicOptions,
} from '../shared/adminAcademicQueries.ts'
import { FOUNDATION_LABELS } from './academicSetupStages.ts'

export function useAcademicSetup(
  accessToken: string,
  initialEntity: AcademicEntity = 'departments',
  allowedEntities: readonly AcademicEntity[] = entities,
) {
  const query = useApiQuery(adminAcademicKeys.setup(accessToken), () => getAcademicCatalogue(accessToken), true, {
    cache: 'navigation',
  })
  const [entity, setEntity] = useState<AcademicEntity>(initialEntity)
  const [editing, setEditing] = useState<AcademicRecord | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<AcademicRecord>({})
  const [department, setDepartment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const data = query.data,
    definition = ACADEMIC_DEFINITIONS[entity]
  const canManage = data?.manageable.includes(entity) ?? false
  const available = allowedEntities.filter((key) => data?.records[key] !== undefined)
  const activeCounts = Object.fromEntries(
    entities.map((key) => [key, data ? records(data, key).filter((row) => usable(data, key, row)).length : 0]),
  ) as Record<AcademicEntity, number>
  const started = available.filter((key) => activeCounts[key] > 0).length
  const suggestedSteps = available.filter(
    (key) => key !== 'program_courses' || !data || !namedOfferingEligibility(data).length,
  )
  const suggested = data
    ? (suggestedSteps.find(
        (key) =>
          activeCounts[key] === 0 && data.manageable.includes(key) && missingPrerequisites(data, key).length === 0,
      ) ?? suggestedSteps.find((key) => activeCounts[key] === 0))
    : undefined
  const missing = data ? missingPrerequisites(data, entity) : []
  const previousStep = available[available.indexOf(entity) - 1]
  const nextStep = available[available.indexOf(entity) + 1]
  const stepNumber = (key: AcademicEntity) => entities.indexOf(key) + 1
  useEffect(() => {
    if (data && data.records[entity] === undefined) {
      const available = allowedEntities.find((key) => data.records[key] !== undefined)
      if (available) {
        setEntity(available)
        setFormOpen(false)
        setEditing(null)
        setForm({})
      }
    }
  }, [data, entity, allowedEntities])
  function reset(next = entity) {
    if (!allowedEntities.includes(next)) return
    setEntity(next)
    setEditing(null)
    setFormOpen(false)
    setForm({})
    setDepartment('')
    setError(null)
    setNotice(null)
  }
  function open(row: AcademicRecord | null) {
    if (!row && missing.length > 0) return
    setEditing(row)
    setFormOpen(true)
    setError(null)
    setNotice(null)
    setForm(row ? { ...row } : { is_active: true, is_current: false, is_required: true })
    setDepartment('')
  }
  function change(field: Pick<Field, 'key'>, value: string | boolean) {
    setForm((previous) => {
      const next = { ...previous, [field.key]: value }
      if (field.key === 'program_id') delete next.course_id
      if (field.key === 'academic_year_id') {
        delete next.semester_id
        if (entity === 'course_offerings') delete next.course_id
      }
      if (field.key === 'semester_id' && entity === 'course_offerings') delete next.course_id
      if (field.key === 'is_active' && value === false) next.is_current = false
      return next
    })
  }
  function choices(field: Field): AcademicRecord[] {
    if (!data || !field.source) return []
    return records(data, field.source).filter((row) => {
      if (editing && row[ACADEMIC_DEFINITIONS[field.source!].id] === form[field.key]) return true
      if (!usable(data, field.source!, row)) return false
      if (field.source === 'programs' && department && row.department_id !== department) return false
      if (field.key === 'semester_id' && entity === 'course_offerings')
        return row.academic_year_id === form.academic_year_id
      if (field.key === 'course_id' && entity === 'course_offerings')
        return (
          Boolean(form.program_id && form.academic_year_id && form.semester_id) &&
          offeringSubjectEligible(data, form.program_id, row.course_id, form.semester_id)
        )
      return true
    })
  }
  function fieldHint(field: Field): string | null {
    if (!field.source || editing) return null
    if (entity === 'course_offerings' && field.key === 'semester_id' && !form.academic_year_id)
      return 'Choose an academic year first to see its semesters.'
    if (
      entity === 'course_offerings' &&
      field.key === 'course_id' &&
      (!form.program_id || !form.academic_year_id || !form.semester_id)
    )
      return 'Choose a program, academic year and semester first to see curriculum subjects.'
    if (choices(field).length > 0 || !field.required) return null
    if (entity === 'course_offerings' && field.key === 'course_id')
      return 'No curriculum subjects match this program and semester. Create a matching named curriculum class in Class Setup, or add a matching link in Step 6: Program Curriculum.'
    if (field.source === 'programs' && department)
      return 'No active programs in this department. Choose another department or add a degree program in College basics.'
    return `No available ${ACADEMIC_DEFINITIONS[field.source].label.toLowerCase()}. Create or activate ${FOUNDATION_LABELS[field.source] ?? ACADEMIC_DEFINITIONS[field.source].label} first.`
  }
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!data || busy) return
    setError(null)
    setNotice(null)
    if (!editing && missing.length > 0) {
      setError('Create or activate the required records before saving this step.')
      return
    }
    if (form.start_date && form.end_date && String(form.end_date) <= String(form.start_date)) {
      setError('End date must follow start date.')
      return
    }
    if (entity === 'batches' && !editing) {
      const start = Number(form.start_year),
        end = Number(form.end_year)
      if (
        !Number.isInteger(start) ||
        !Number.isInteger(end) ||
        start < 1900 ||
        start > 2200 ||
        end <= start ||
        end > start + 10
      ) {
        setError('Enter an admission year and a completion year 1 to 10 years later, for example 2026–2030.')
        return
      }
    }
    if (entity === 'semesters') {
      const year = find(data, 'academic_years', form.academic_year_id)
      if (
        year &&
        (String(form.start_date) < String(year.start_date) || String(form.end_date) > String(year.end_date))
      ) {
        setError('Semester dates must fit within the selected academic year.')
        return
      }
    }
    const payload: AcademicRecord = { is_active: form.is_active ?? true }
    for (const field of definition.fields) {
      if (editing && field.immutable) continue
      const value = form[field.key]
      if (field.type === 'checkbox') payload[field.key] = Boolean(value)
      else if (value !== undefined && value !== null && value !== '')
        payload[field.key] = field.type === 'number' ? Number(value) : String(value).trim()
      else if (!field.required) payload[field.key] = null
    }
    setBusy(true)
    try {
      await saveAcademicRecord(accessToken, entity, payload, editing ? String(editing[definition.id]) : undefined)
      setFormOpen(false)
      setEditing(null)
      setNotice('Academic record saved.')
      await Promise.all([
        query.refetch(),
        invalidateFacultyAcademicOptions(accessToken),
        invalidateAcademicPackageOptions(accessToken),
      ])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save academic record.')
    } finally {
      setBusy(false)
    }
  }
  return {
    query,
    data,
    entity,
    definition,
    canManage,
    available,
    activeCounts,
    started,
    suggested,
    missing,
    previousStep,
    nextStep,
    stepNumber,
    reset,
    open,
    editing,
    formOpen,
    setFormOpen,
    form,
    setForm,
    department,
    setDepartment,
    busy,
    error,
    notice,
    change,
    choices,
    fieldHint,
    save,
  }
}
export type AcademicSetupState = ReturnType<typeof useAcademicSetup>

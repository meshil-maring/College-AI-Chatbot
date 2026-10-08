import { useState, type FormEvent } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { getAcademicCatalogue, saveAcademicRecord } from '../../services/adminApi.ts'
import type { AcademicCatalogue, AcademicEntity, AcademicRecord } from '../../types/academicSetup.ts'

type Field = { key: string; label: string; type?: 'number' | 'date' | 'checkbox' | 'textarea'; required?: boolean; source?: AcademicEntity; options?: string[]; immutable?: boolean; min?: number }
type Definition = { label: string; id: string; help: string; fields: Field[] }
const named: Field[] = [{ key: 'name', label: 'Name', required: true }, { key: 'code', label: 'Code', required: true }]
const description: Field = { key: 'description', label: 'Description', type: 'textarea' }
const dates: Field[] = [{ key: 'start_date', label: 'Start date', type: 'date', required: true }, { key: 'end_date', label: 'End date', type: 'date', required: true }, { key: 'is_current', label: 'Current', type: 'checkbox' }]
const parent = (key: string, label: string, source: AcademicEntity, required = true): Field => ({ key, label, source, required, immutable: true })
const capacity: Field = { key: 'capacity', label: 'Capacity', type: 'number', min: 1 }
export const ACADEMIC_DEFINITIONS: Record<AcademicEntity, Definition> = {
  departments: { label: 'Departments', id: 'department_id', help: 'Define the departments within your institution.', fields: [...named, description] },
  programs: { label: 'Programs', id: 'program_id', help: 'Create a degree program in an active department.', fields: [parent('department_id', 'Department', 'departments'), ...named, { key: 'degree_type', label: 'Degree type', required: true }, { key: 'duration_years', label: 'Duration in years', type: 'number', min: 0.01, required: true }, { key: 'total_credits', label: 'Total credits', type: 'number', min: 0.01 }, description] },
  academic_years: { label: 'Academic Years', id: 'academic_year_id', help: 'Set year dates. Active years cannot overlap; only one can be current.', fields: [...named, ...dates] },
  semesters: { label: 'Semesters', id: 'semester_id', help: 'Create terms within an academic year. Programs use these terms through course offerings.', fields: [parent('academic_year_id', 'Academic year', 'academic_years'), ...named, { key: 'semester_number', label: 'Semester number', type: 'number', min: 1, required: true }, ...dates] },
  courses: { label: 'Courses / Subjects', id: 'course_id', help: 'Define subjects once, then connect them to a program curriculum.', fields: [parent('department_id', 'Department', 'departments'), ...named, { key: 'credits', label: 'Credits', type: 'number', min: 0.01 }, ...['lecture', 'tutorial', 'practical'].map((kind): Field => ({ key: `${kind}_hours`, label: `${kind[0].toUpperCase()}${kind.slice(1)} hours`, type: 'number', min: 0 })), description] },
  program_courses: { label: 'Program Curriculum', id: 'program_course_id', help: 'Link a subject to a program before creating its offering. Subjects may come from any department in this institution.', fields: [parent('program_id', 'Program', 'programs'), parent('course_id', 'Course / subject', 'courses'), parent('semester_id', 'Semester (optional)', 'semesters', false), { key: 'course_type', label: 'Course type', required: true, options: ['core', 'elective', 'open_elective', 'skill', 'project'] }, { key: 'is_required', label: 'Required subject', type: 'checkbox' }] },
  course_offerings: { label: 'Course Offerings', id: 'course_offering_id', help: 'Schedule a curriculum subject for a program, academic year and semester.', fields: [parent('program_id', 'Program', 'programs'), parent('academic_year_id', 'Academic year', 'academic_years'), parent('semester_id', 'Semester', 'semesters'), parent('course_id', 'Course / subject', 'courses'), capacity] },
  sections: { label: 'Sections', id: 'section_id', help: 'Create a subject section within an offering. Use the same section code for sibling subjects belonging to the same class.', fields: [parent('course_offering_id', 'Course offering', 'course_offerings'), { key: 'name', label: 'Name', required: true }, { key: 'code', label: 'Section code', required: true, immutable: true }, capacity] },
}
const entities = Object.keys(ACADEMIC_DEFINITIONS) as AcademicEntity[]
const inputClass = 'mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 p-2 text-slate-100 disabled:opacity-60'
function records(data: AcademicCatalogue, entity: AcademicEntity): AcademicRecord[] { return data.records[entity] ?? [] }
function find(data: AcademicCatalogue, entity: AcademicEntity, id: unknown) { return records(data, entity).find((row) => row[ACADEMIC_DEFINITIONS[entity].id] === id) }
export function usable(data: AcademicCatalogue, entity: AcademicEntity, row: AcademicRecord): boolean {
  if (!row.is_active) return false
  const ancestry: Partial<Record<AcademicEntity, [AcademicEntity, string][]>> = {
    programs: [['departments', 'department_id']], courses: [['departments', 'department_id']],
    semesters: [['academic_years', 'academic_year_id']],
    program_courses: [['programs', 'program_id'], ['courses', 'course_id']],
    course_offerings: [['programs', 'program_id'], ['courses', 'course_id'], ['academic_years', 'academic_year_id'], ['semesters', 'semester_id']],
    sections: [['course_offerings', 'course_offering_id']],
  }
  return (ancestry[entity] ?? []).every(([source, key]) => { const value = find(data, source, row[key]); return value !== undefined && usable(data, source, value) })
}
function label(data: AcademicCatalogue, entity: AcademicEntity, row: AcademicRecord): string {
  if (entity === 'course_offerings' || entity === 'program_courses') {
    const subject = find(data, 'courses', row.course_id), program = find(data, 'programs', row.program_id), term = find(data, 'semesters', row.semester_id)
    const year = find(data, 'academic_years', row.academic_year_id ?? term?.academic_year_id)
    return [program?.code, subject?.code, year?.name, term?.name].filter(Boolean).join(' · ')
  }
  return `${row.code} · ${row.name}`
}

export default function AcademicSetup({ accessToken }: { accessToken: string }) {
  return <AcademicSetupWorkspace key={accessToken} accessToken={accessToken} />
}
function AcademicSetupWorkspace({ accessToken }: { accessToken: string }) {
  const query = useApiQuery(['admin', 'academic-setup', accessToken], () => getAcademicCatalogue(accessToken))
  const [entity, setEntity] = useState<AcademicEntity>('departments')
  const [editing, setEditing] = useState<AcademicRecord | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<AcademicRecord>({})
  const [department, setDepartment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const data = query.data, definition = ACADEMIC_DEFINITIONS[entity]
  const canManage = data?.manageable.includes(entity) ?? false
  function reset(next = entity) { setEntity(next); setEditing(null); setFormOpen(false); setForm({}); setDepartment(''); setError(null); setNotice(null) }
  function open(row: AcademicRecord | null) { setEditing(row); setFormOpen(true); setError(null); setNotice(null); setForm(row ? { ...row } : { is_active: true, is_current: false, is_required: true }); setDepartment('') }
  function change(field: Field, value: string | boolean) {
    setForm((previous) => {
      const next = { ...previous, [field.key]: value }
      if (field.key === 'program_id') delete next.course_id
      if (field.key === 'academic_year_id') { delete next.semester_id; if (entity === 'course_offerings') delete next.course_id }
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
      if (field.key === 'semester_id' && entity === 'course_offerings') return row.academic_year_id === form.academic_year_id
      if (field.key === 'course_id' && entity === 'course_offerings') return records(data, 'program_courses').some((link) => link.is_active && link.program_id === form.program_id && link.course_id === row.course_id && (!link.semester_id || link.semester_id === form.semester_id))
      return true
    })
  }
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!data || busy) return
    setError(null); setNotice(null)
    if (form.start_date && form.end_date && String(form.end_date) <= String(form.start_date)) { setError('End date must follow start date.'); return }
    if (entity === 'semesters') {
      const year = find(data, 'academic_years', form.academic_year_id)
      if (year && (String(form.start_date) < String(year.start_date) || String(form.end_date) > String(year.end_date))) { setError('Semester dates must fit within the selected academic year.'); return }
    }
    const payload: AcademicRecord = { is_active: form.is_active ?? true }
    for (const field of definition.fields) {
      if (editing && field.immutable) continue
      const value = form[field.key]
      if (field.type === 'checkbox') payload[field.key] = Boolean(value)
      else if (value !== undefined && value !== null && value !== '') payload[field.key] = field.type === 'number' ? Number(value) : String(value).trim()
      else if (!field.required) payload[field.key] = null
    }
    setBusy(true)
    try {
      await saveAcademicRecord(accessToken, entity, payload, editing ? String(editing[definition.id]) : undefined)
      setFormOpen(false); setEditing(null); setNotice('Academic record saved.'); await query.refetch()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save academic record.') }
    finally { setBusy(false) }
  }
  return <section className="space-y-5" aria-label="Academic setup workspace">
    <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5"><h2 className="text-lg font-semibold">Institution academic structure</h2><p className="mt-2 text-sm text-slate-300">Enter your institution’s real academic records, then create teaching assignments. Start with departments, programs and academic years; add semesters, subjects, curriculum links, offerings and sections.</p><p className="mt-2 text-sm text-slate-400">Student enrollment uses the existing student approval and Faculty roster workflows.</p></div>
    {query.isPending ? <p role="status">Loading academic setup…</p> : null}
    {query.isError ? <div role="alert"><p>{query.error instanceof Error ? query.error.message : 'Could not load academic setup.'}</p><button className="mt-2 rounded-lg border border-slate-600 px-3 py-2" onClick={() => void query.refetch()}>Retry loading</button></div> : null}
    {data ? <>
      <nav aria-label="Academic setup entities" className="flex flex-wrap gap-2">{entities.filter((key) => data.records[key] !== undefined).map((key) => <button key={key} disabled={busy} aria-current={entity === key ? 'page' : undefined} className={`rounded-lg border px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-400 ${entity === key ? 'border-emerald-600 bg-emerald-700' : 'border-slate-600 bg-slate-800'}`} onClick={() => reset(key)}>{ACADEMIC_DEFINITIONS[key].label} <span className="ml-1 text-xs opacity-70">{records(data, key).length}</span></button>)}</nav>
      <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-semibold">{definition.label}</h2><p className="mt-1 text-sm text-slate-300">{definition.help}</p></div>{canManage ? <button disabled={busy} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm disabled:opacity-50" onClick={() => open(null)}>Add record</button> : <p className="text-sm text-slate-400">Read-only access</p>}</div>
        {error ? <p role="alert" className="mt-4 rounded-lg border border-red-700 p-3 text-red-200">{error}</p> : null}
        {notice ? <p role="status" className="mt-4 text-emerald-300">{notice}</p> : null}
        {formOpen && canManage ? <form onSubmit={(event) => void save(event)} className="mt-5 space-y-4 rounded-xl border border-slate-600 p-4">
          <h3 className="font-semibold">{editing ? 'Edit record' : 'New record'}</h3>
          {editing ? <p className="text-xs text-slate-400">Academic relationships are fixed after creation. Deactivation preserves dependent records and history.</p> : null}
          {!editing && ['program_courses', 'course_offerings'].includes(entity) ? <label className="block text-sm">Program department filter<select value={department} onChange={(event) => { setDepartment(event.target.value); setForm((previous) => ({ ...previous, program_id: '', course_id: '' })) }} className={inputClass}><option value="">All active departments</option>{records(data, 'departments').filter((row) => usable(data, 'departments', row)).map((row) => <option key={String(row.department_id)} value={String(row.department_id)}>{label(data, 'departments', row)}</option>)}</select></label> : null}
          <fieldset disabled={busy} className="grid gap-4 md:grid-cols-2">{definition.fields.map((field) => <label key={field.key} className="block text-sm">{field.label}{field.required ? ' *' : ''}
            {field.source || field.options ? <select required={field.required} disabled={Boolean(editing && field.immutable)} value={String(form[field.key] ?? '')} onChange={(event) => change(field, event.target.value)} className={inputClass}><option value="">{field.required ? 'Select a record' : 'Any semester'}</option>{field.source ? choices(field).map((row) => <option key={String(row[ACADEMIC_DEFINITIONS[field.source!].id])} value={String(row[ACADEMIC_DEFINITIONS[field.source!].id])}>{label(data, field.source!, row)}</option>) : field.options?.map((option) => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}</select>
              : field.type === 'checkbox' ? <input type="checkbox" checked={Boolean(form[field.key])} disabled={field.key === 'is_current' && !form.is_active} onChange={(event) => change(field, event.target.checked)} className="ml-3 accent-emerald-500" />
                : field.type === 'textarea' ? <textarea maxLength={4000} value={String(form[field.key] ?? '')} onChange={(event) => change(field, event.target.value)} className={inputClass} />
                  : <input required={field.required} maxLength={field.type ? undefined : 200} disabled={Boolean(editing && field.immutable)} type={field.type ?? 'text'} min={field.min} step={field.type === 'number' ? ['capacity', 'semester_number'].includes(field.key) ? '1' : '0.01' : undefined} value={String(form[field.key] ?? '')} onChange={(event) => change(field, event.target.value)} className={inputClass} />}
          </label>)}<label className="text-sm">Active<input type="checkbox" checked={Boolean(form.is_active)} onChange={(event) => change({ key: 'is_active', label: 'Active' }, event.target.checked)} className="ml-3 accent-emerald-500" /></label></fieldset>
          <div className="flex gap-3"><button disabled={busy} type="submit" className="rounded-lg bg-emerald-700 px-4 py-2 text-sm disabled:opacity-50">{busy ? 'Saving…' : 'Save record'}</button><button type="button" disabled={busy} onClick={() => setFormOpen(false)} className="rounded-lg border border-slate-600 px-4 py-2 text-sm">Cancel</button></div>
        </form> : null}
        {records(data, entity).length === 0 ? <p role="status" className="mt-6 text-sm text-slate-400">No {definition.label.toLowerCase()} have been entered. Add your institution’s real records to continue.</p> : <ul className="mt-5 divide-y divide-slate-700">{records(data, entity).map((row) => <li key={String(row[definition.id])} className="flex flex-wrap items-center gap-3 py-3"><div className="mr-auto"><p className="text-sm font-medium">{label(data, entity, row)}</p><p className="mt-1 text-xs text-slate-400">{row.is_active ? usable(data, entity, row) ? 'Active' : 'Unavailable: an academic parent is inactive' : 'Inactive'}{row.is_current ? ' · Current' : ''}{row.start_date ? ` · ${row.start_date} – ${row.end_date}` : ''}</p></div>{canManage ? <button disabled={busy} className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm" onClick={() => open(row)}>Edit {String(row.code ?? 'offering')}</button> : null}</li>)}</ul>}
      </div>
    </> : null}
  </section>
}

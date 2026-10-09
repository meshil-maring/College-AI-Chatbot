import { useEffect, useState, type FormEvent } from 'react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { getAcademicCatalogue, saveAcademicRecord } from '../../services/adminApi.ts'
import type { AcademicCatalogue, AcademicEntity, AcademicRecord } from '../../types/academicSetup.ts'
import AcademicSetupHelp from './AcademicSetupHelp.tsx'
import { ACADEMIC_DEFINITIONS, ACADEMIC_ENTITIES as entities, type AcademicField as Field } from './academicSetupDefinitions.ts'

export { ACADEMIC_DEFINITIONS } from './academicSetupDefinitions.ts'
const inputClass = 'mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 p-2 text-slate-100 disabled:opacity-60'
function records(data: AcademicCatalogue, entity: AcademicEntity): AcademicRecord[] { return data.records[entity] ?? [] }
function find(data: AcademicCatalogue, entity: AcademicEntity, id: unknown) { return records(data, entity).find((row) => row[ACADEMIC_DEFINITIONS[entity].id] === id) }
export function usable(data: AcademicCatalogue, entity: AcademicEntity, row: AcademicRecord): boolean {
  if (!row.is_active) return false
  const ancestry: Partial<Record<AcademicEntity, [AcademicEntity, string][]>> = {
    programs: [['departments', 'department_id']], courses: [['departments', 'department_id']],
    semesters: [['academic_years', 'academic_year_id']],
    program_courses: [['programs', 'program_id'], ['courses', 'course_id'], ...(row.semester_id ? [['semesters', 'semester_id'] as [AcademicEntity, string]] : [])],
    course_offerings: [['programs', 'program_id'], ['courses', 'course_id'], ['academic_years', 'academic_year_id'], ['semesters', 'semester_id']],
    sections: [['course_offerings', 'course_offering_id']],
  }
  return (ancestry[entity] ?? []).every(([source, key]) => { const value = find(data, source, row[key]); return value !== undefined && usable(data, source, value) })
}
function missingPrerequisites(data: AcademicCatalogue, entity: AcademicEntity): AcademicEntity[] {
  return ACADEMIC_DEFINITIONS[entity].requires.filter((source) => !records(data, source).some((row) => usable(data, source, row)))
}
function label(data: AcademicCatalogue, entity: AcademicEntity, row: AcademicRecord): string {
  if (entity === 'course_offerings' || entity === 'program_courses') {
    const subject = find(data, 'courses', row.course_id), program = find(data, 'programs', row.program_id), term = find(data, 'semesters', row.semester_id)
    const year = find(data, 'academic_years', row.academic_year_id ?? term?.academic_year_id)
    return [program?.code, subject?.code, year?.name, term?.name].filter(Boolean).join(' · ')
  }
  if (entity === 'semesters') return `${find(data, 'academic_years', row.academic_year_id)?.name ?? ''} · ${row.code} · ${row.name}`
  if (entity === 'sections') {
    const offering = find(data, 'course_offerings', row.course_offering_id)
    return `${offering ? label(data, 'course_offerings', offering) : ''} · ${row.code} · ${row.name}`
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
  const available = entities.filter((key) => data?.records[key] !== undefined)
  const activeCounts = Object.fromEntries(entities.map((key) => [key, data ? records(data, key).filter((row) => usable(data, key, row)).length : 0])) as Record<AcademicEntity, number>
  const started = available.filter((key) => activeCounts[key] > 0).length
  const suggested = data ? available.find((key) => activeCounts[key] === 0 && data.manageable.includes(key) && missingPrerequisites(data, key).length === 0)
    ?? available.find((key) => activeCounts[key] === 0) : undefined
  const missing = data ? missingPrerequisites(data, entity) : []
  const previousStep = available[available.indexOf(entity) - 1]
  const nextStep = available[available.indexOf(entity) + 1]
  const stepNumber = (key: AcademicEntity) => entities.indexOf(key) + 1
  useEffect(() => {
    if (data && data.records[entity] === undefined) {
      const available = entities.find((key) => data.records[key] !== undefined)
      if (available) { setEntity(available); setFormOpen(false); setEditing(null); setForm({}) }
    }
  }, [data, entity])
  function reset(next = entity) { setEntity(next); setEditing(null); setFormOpen(false); setForm({}); setDepartment(''); setError(null); setNotice(null) }
  function open(row: AcademicRecord | null) { if (!row && missing.length > 0) return; setEditing(row); setFormOpen(true); setError(null); setNotice(null); setForm(row ? { ...row } : { is_active: true, is_current: false, is_required: true }); setDepartment('') }
  function change(field: Pick<Field, 'key'>, value: string | boolean) {
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
      if (field.key === 'course_id' && entity === 'course_offerings') return Boolean(form.program_id && form.academic_year_id && form.semester_id) && records(data, 'program_courses').some((link) => link.is_active && link.program_id === form.program_id && link.course_id === row.course_id && (!link.semester_id || link.semester_id === form.semester_id))
      return true
    })
  }
  function fieldHint(field: Field): string | null {
    if (!field.source || editing) return null
    if (entity === 'course_offerings' && field.key === 'semester_id' && !form.academic_year_id) return 'Choose an academic year first to see its semesters.'
    if (entity === 'course_offerings' && field.key === 'course_id' && (!form.program_id || !form.academic_year_id || !form.semester_id)) return 'Choose a program, academic year and semester first to see curriculum subjects.'
    if (choices(field).length > 0 || !field.required) return null
    if (entity === 'course_offerings' && field.key === 'course_id') return 'No curriculum subjects match this program and semester. Add a matching link in Step 6: Program Curriculum.'
    if (field.source === 'programs' && department) return 'No active programs in this department. Choose another department or add a program in Step 2.'
    return `No available ${ACADEMIC_DEFINITIONS[field.source].label.toLowerCase()}. Create or activate a record in Step ${stepNumber(field.source)} first.`
  }
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!data || busy) return
    setError(null); setNotice(null)
    if (!editing && missing.length > 0) { setError('Create or activate the required records before saving this step.'); return }
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
    <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5">
      <h2 className="text-lg font-semibold">Set up your college, step by step</h2>
      <p className="mt-2 text-sm text-slate-300">Follow the numbered steps below. Add your college’s records at each step, then continue to the next. You can return to any step to add more.</p>
      <p className="mt-2 text-sm text-slate-400">Use the <span className="font-semibold text-emerald-300">ⓘ</span> beside a field for a short explanation. Hover, focus or tap to read it.</p>
      {data ? <div className="mt-4 space-y-2">
        <p className="text-sm font-medium text-emerald-300">{started} of {available.length} available steps have active records</p>
        <div role="progressbar" aria-label="Steps with active records" aria-valuenow={started} aria-valuemin={0} aria-valuemax={available.length} className="h-2 overflow-hidden rounded-full bg-slate-700">
          <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${available.length ? started / available.length * 100 : 0}%` }} />
        </div>
        <p className="text-xs text-slate-400">This tracks steps with at least one usable record. Add every department, program, subject and teaching group your college needs.</p>
        {suggested ? <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-800 bg-emerald-950/40 p-3">
          <div><p className="text-sm font-medium">Suggested next step: {stepNumber(suggested)}. {ACADEMIC_DEFINITIONS[suggested].label}</p><p className="mt-1 text-xs text-slate-300">{ACADEMIC_DEFINITIONS[suggested].help}</p></div>
          <button type="button" disabled={busy || formOpen} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-400 disabled:opacity-50" onClick={() => reset(suggested)}>Go to {ACADEMIC_DEFINITIONS[suggested].label}</button>
        </div> : <p className="text-sm text-emerald-300">All available steps have active records. Review your setup and add any remaining records.</p>}
      </div> : null}
    </div>
    {query.isPending ? <p role="status">Loading academic setup…</p> : null}
    {query.isError ? <div role="alert"><p>{query.error instanceof Error ? query.error.message : 'Could not load academic setup.'}</p><button className="mt-2 rounded-lg border border-slate-600 px-3 py-2" onClick={() => void query.refetch()}>Retry loading</button></div> : null}
    {data ? <>
      <nav aria-label="Academic setup entities">
        <ol className="grid grid-cols-2 gap-2 xl:grid-cols-4">{available.map((key) => <li key={key}>
          <button type="button" disabled={busy || formOpen} aria-current={entity === key ? 'step' : undefined} aria-label={`${ACADEMIC_DEFINITIONS[key].label}, Step ${stepNumber(key)}, ${activeCounts[key]} active records`}
            className={`h-full w-full rounded-xl border p-3 text-left focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:opacity-60 ${entity === key ? 'border-emerald-500 bg-emerald-950/50' : 'border-slate-700 bg-slate-800 hover:border-slate-500'}`} onClick={() => reset(key)}>
            <span className="flex items-center gap-2"><span aria-hidden="true" className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${activeCounts[key] ? 'bg-emerald-700 text-white' : 'bg-slate-700 text-slate-300'}`}>{stepNumber(key)}</span><span className="min-w-0 break-words text-sm font-medium">{ACADEMIC_DEFINITIONS[key].label}</span></span>
            <span className={`mt-2 block text-xs ${activeCounts[key] ? 'text-emerald-300' : 'text-slate-400'}`}>{activeCounts[key] ? `${activeCounts[key]} active ${activeCounts[key] === 1 ? 'record' : 'records'}` : missingPrerequisites(data, key).length ? 'Needs earlier setup' : 'Add your first record'}</span>
          </button>
        </li>)}</ol>
      </nav>
      <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-300">Step {stepNumber(entity)} of {entities.length}</p><h2 className="text-lg font-semibold">{definition.label}</h2><p className="mt-1 text-sm text-slate-300">{definition.help}</p></div>
          {canManage ? <button disabled={busy || missing.length > 0 || formOpen} aria-describedby={missing.length ? 'academic-prerequisites' : undefined} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm disabled:opacity-50" onClick={() => open(null)}>Add record</button> : <p className="text-sm text-slate-400">Read-only access</p>}
        </div>
        <p className="mt-3 rounded-lg bg-slate-900/60 p-3 text-sm text-slate-300"><span className="font-medium text-slate-100">Example: </span>{definition.example}. Use your college’s actual names, codes and dates.</p>
        {missing.length ? <div id="academic-prerequisites" className="mt-4 rounded-xl border border-amber-700/60 bg-amber-950/20 p-4">
          <h3 className="text-sm font-semibold text-amber-200">Before adding {definition.label.toLowerCase()}</h3>
          <p className="mt-1 text-sm text-slate-300">You need active records from the following steps. Inactive records and records with inactive parents cannot be selected.</p>
          <ul className="mt-3 space-y-2">{missing.map((key) => <li key={key} className="text-sm">
            {data.records[key] === undefined ? <p className="text-amber-200">Step {stepNumber(key)}: {ACADEMIC_DEFINITIONS[key].label} — ask an administrator with access to this step for help.</p>
              : <><button type="button" disabled={busy || formOpen} onClick={() => reset(key)} className="rounded-lg border border-amber-700 px-3 py-2 text-amber-200 focus:ring-2 focus:ring-amber-400 disabled:opacity-50">Open Step {stepNumber(key)}: {ACADEMIC_DEFINITIONS[key].label}</button>{!data.manageable.includes(key) ? <span className="ml-2 text-xs text-slate-300">Read-only: ask an administrator to add or activate a record.</span> : null}</>}
          </li>)}</ul>
        </div> : null}
        {error ? <p role="alert" className="mt-4 rounded-lg border border-red-700 p-3 text-red-200">{error}</p> : null}
        {notice ? <div className="mt-4"><p role="status" className="text-emerald-300">{notice}</p><p className="mt-1 text-sm text-slate-300">Add another record if needed, or use the next step below to continue.</p></div> : null}
        {formOpen && canManage ? <form onSubmit={(event) => void save(event)} className="mt-5 space-y-4 rounded-xl border border-slate-600 p-4">
          <h3 className="font-semibold">{editing ? 'Edit record' : 'New record'}</h3>
          <p className="text-xs text-slate-400">Fields marked * are required. Other fields can be left blank.</p>
          {editing ? <p className="text-xs text-slate-400">Academic relationships are fixed after creation. Deactivation preserves dependent records and history.</p> : null}
          {!editing && ['program_courses', 'course_offerings'].includes(entity) ? <div className="text-sm">
            <div className="flex items-center gap-1"><label htmlFor="academic-department-filter">Program department filter</label><AcademicSetupHelp label="Program department filter">Optionally narrow the program list to one department. This does not restrict which department a subject belongs to.</AcademicSetupHelp></div>
            <select id="academic-department-filter" disabled={busy} value={department} onChange={(event) => { setDepartment(event.target.value); setForm((previous) => ({ ...previous, program_id: '', course_id: '' })) }} className={inputClass}>
              <option value="">All active departments</option>{records(data, 'departments').filter((row) => usable(data, 'departments', row)).map((row) => <option key={String(row.department_id)} value={String(row.department_id)}>{label(data, 'departments', row)}</option>)}
            </select>
          </div> : null}
          <fieldset disabled={busy} className="grid gap-4 md:grid-cols-2">
            {definition.fields.map((field) => {
              const id = `academic-${entity}-${field.key}`
              const hint = fieldHint(field)
              const describedBy = `${id}-help${hint ? ` ${id}-hint` : ''}`
              return <div key={field.key} className="min-w-0 text-sm">
                <div className="flex items-center gap-1"><label htmlFor={id}>{field.label}{field.required ? ' *' : ''}</label><AcademicSetupHelp label={field.label}>{field.help}</AcademicSetupHelp>
                  {field.type === 'checkbox' ? <input id={id} aria-describedby={describedBy} type="checkbox" checked={Boolean(form[field.key])} disabled={field.key === 'is_current' && !form.is_active} onChange={(event) => change(field, event.target.checked)} className="ml-2 accent-emerald-500" /> : null}
                </div>
                <span id={`${id}-help`} className="sr-only">{field.help}</span>
                {field.source || field.options ? <select id={id} aria-describedby={describedBy} required={field.required} disabled={Boolean(editing && field.immutable)} value={String(form[field.key] ?? '')} onChange={(event) => change(field, event.target.value)} className={inputClass}>
                  <option value="">{field.required ? `Select ${field.label.toLowerCase()}` : 'Any semester'}</option>{field.source ? choices(field).map((row) => <option key={String(row[ACADEMIC_DEFINITIONS[field.source!].id])} value={String(row[ACADEMIC_DEFINITIONS[field.source!].id])}>{label(data, field.source!, row)}</option>) : field.options?.map((option) => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}
                </select> : field.type === 'textarea' ? <textarea id={id} aria-describedby={describedBy} maxLength={4000} placeholder={field.placeholder} value={String(form[field.key] ?? '')} onChange={(event) => change(field, event.target.value)} className={inputClass} />
                  : field.type !== 'checkbox' ? <input id={id} aria-describedby={describedBy} required={field.required} maxLength={field.type ? undefined : 200} placeholder={field.placeholder} disabled={Boolean(editing && field.immutable)} type={field.type ?? 'text'} min={field.min} step={field.type === 'number' ? ['capacity', 'semester_number'].includes(field.key) ? '1' : '0.01' : undefined} value={String(form[field.key] ?? '')} onChange={(event) => change(field, event.target.value)} className={inputClass} /> : null}
                {hint ? <p id={`${id}-hint`} className="mt-2 text-xs text-amber-200">{hint}</p> : null}
              </div>
            })}
            <div className="text-sm"><div className="flex items-center gap-1"><label htmlFor="academic-is-active">Active</label><AcademicSetupHelp label="Active">Keep checked to make this record available in later steps. Unchecking retains the record and its history, but makes it and dependent records unavailable for new selections.</AcademicSetupHelp><input id="academic-is-active" type="checkbox" checked={Boolean(form.is_active)} onChange={(event) => change({ key: 'is_active' }, event.target.checked)} className="ml-2 accent-emerald-500" /></div></div>
          </fieldset>
          <div className="flex gap-3"><button disabled={busy || (!editing && missing.length > 0)} type="submit" className="rounded-lg bg-emerald-700 px-4 py-2 text-sm disabled:opacity-50">{busy ? 'Saving…' : 'Save record'}</button><button type="button" disabled={busy} onClick={() => setFormOpen(false)} className="rounded-lg border border-slate-600 px-4 py-2 text-sm">Cancel</button></div>
        </form> : null}
        {records(data, entity).length === 0 ? <p role="status" className="mt-6 text-sm text-slate-400">No {definition.label.toLowerCase()} have been entered. {canManage ? missing.length ? 'Follow the prerequisite steps above to continue.' : 'Select Add record to enter your college’s first record.' : 'Ask an administrator with management access to add records.'}</p>
          : <ul className="mt-5 divide-y divide-slate-700">{records(data, entity).map((row) => <li key={String(row[definition.id])} className="flex flex-wrap items-center gap-3 py-3"><div className="mr-auto"><p className="text-sm font-medium">{label(data, entity, row)}</p><p className="mt-1 text-xs text-slate-400">{row.is_active ? usable(data, entity, row) ? 'Active' : 'Unavailable: an academic parent is inactive' : 'Inactive'}{row.is_current ? ' · Current' : ''}{row.start_date ? ` · ${row.start_date} – ${row.end_date}` : ''}</p></div>{canManage ? <button disabled={busy || formOpen} className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm" onClick={() => open(row)}>Edit {String(row.code ?? 'offering')}</button> : null}</li>)}</ul>}
        <div className="mt-5 border-t border-slate-700 pt-4">
          {formOpen ? <p className="mb-3 text-xs text-slate-400">Save or cancel this record before changing steps.</p> : null}
          <div className="flex flex-wrap justify-between gap-3">
            <button type="button" disabled={busy || formOpen || !previousStep} onClick={() => previousStep && reset(previousStep)} className="rounded-lg border border-slate-600 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-400 disabled:opacity-40">Previous step</button>
            {nextStep ? <button type="button" disabled={busy || formOpen} onClick={() => reset(nextStep)} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-400 disabled:opacity-50">Next: {ACADEMIC_DEFINITIONS[nextStep].label}</button> : null}
          </div>
          {entity === 'sections' ? <p className="mt-4 text-sm text-slate-300">After adding your sections, open Faculty Assignments in the Admin menu to assign teachers. Student enrollment continues through Student Approvals and the Faculty roster.</p> : null}
        </div>
      </div>
    </> : null}
  </section>
}

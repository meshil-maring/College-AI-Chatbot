import { useEffect, useMemo, useRef, useState } from 'react'
import { ClipboardCheck, Plus, RefreshCw } from 'lucide-react'
import {
  commitTestImport, correctTestImport, createTest, getTest, getTestHistory, getTestImport, getTestResources,
  getTests, getTestTypes, saveTestMarks, transitionTest, updateTest, uploadTestMarks,
  type FacultyTest, type MarksDetail, type TestHistory, type TestImport, type TestInput, type TestList,
} from '../../services/facultyTestsApi.ts'
import type { AttendanceSection } from '../../services/facultyAttendanceApi.ts'
import { AttendanceAcademicFilters } from './attendance/AttendanceRecordedViews.tsx'
import { AttendanceMetric } from './attendance/AttendancePrimitives.tsx'
import TestForm, { button, field, surface } from './tests/TestForm.tsx'
import MarksEditor from './tests/MarksEditor.tsx'
import MarksImportReview from './tests/MarksImportReview.tsx'

type View = 'overview' | 'tests' | 'create' | 'marks' | 'results' | 'import' | 'history'
const labels: Record<View, string> = { overview: 'Overview', tests: 'My Tests', create: 'Create Test', marks: 'Enter Marks', results: 'Results', import: 'Import', history: 'History' }

export default function FacultyTests({ accessToken, scopeVersion = '', onDirtyChange }: {
  accessToken: string; scopeVersion?: string; onDirtyChange?: (dirty: boolean) => void
}) {
  const [scopes, setScopes] = useState<AttendanceSection[]>([])
  const [types, setTypes] = useState<Array<{ code: string; name: string }>>([])
  const [section, setSection] = useState('')
  const [list, setList] = useState<TestList | null>(null)
  const [testId, setTestId] = useState('')
  const [detail, setDetail] = useState<MarksDetail | null>(null)
  const [history, setHistory] = useState<TestHistory | null>(null)
  const [item, setItem] = useState<TestImport | null>(null)
  const [view, setView] = useState<View>('overview')
  const [editing, setEditing] = useState(false)
  const [page, setPage] = useState(0)
  const [tick, setTick] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [unsaved, setUnsaved] = useState(false)
  const dirty = useRef(false)
  const generation = useRef(0)
  const selectedSection = useRef(section)
  selectedSection.current = section
  const scope = scopes.find(s => s.section_id === section)
  const t = detail?.test
  function setDirty(value: boolean) { dirty.current = value; setUnsaved(value); onDirtyChange?.(value) }
  function canLeave() { if (!dirty.current || window.confirm('Discard unsaved assessment changes?')) { setDirty(false); return true }; return false }
  function navigate(next: View) { if (canLeave()) { setEditing(false); setView(next); setSuccess('') } }

  useEffect(() => {
    const unload = (e: BeforeUnloadEvent) => { if (dirty.current) { e.preventDefault(); e.returnValue = '' } }
    const focus = () => { if (!dirty.current) setTick(n => n + 1) }
    window.addEventListener('beforeunload', unload); window.addEventListener('focus', focus)
    return () => { window.removeEventListener('beforeunload', unload); window.removeEventListener('focus', focus) }
  }, [])
  useEffect(() => {
    let live = true
    generation.current++; setDirty(false); setScopes([]); setTestId(''); setDetail(null); setItem(null); setHistory(null); setList(null); setLoading(true); setError(''); setBusy(false); setView('overview')
    Promise.all([getTestResources(accessToken), getTestTypes(accessToken)]).then(([resources, catalog]) => {
      if (!live) return
      setScopes(resources); setTypes(catalog)
      setSection(current => resources.some(s => s.section_id === current) ? current : resources[0]?.section_id ?? '')
    }).catch((e: unknown) => { if (live) { setSection(''); setError(e instanceof Error ? e.message : 'Unable to load assessment scopes') } })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
    // Context changes invalidate every cached workflow and authority.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, scopeVersion])
  useEffect(() => {
    if (!tick) return
    let live = true
    getTestResources(accessToken).then(resources => {
      if (!live) return
      setScopes(resources)
      if (!resources.some(s => s.section_id === selectedSection.current)) {
        setTestId(''); setDetail(null); setItem(null); setHistory(null); setList(null); setView('overview')
        setSection(resources[0]?.section_id ?? '')
      }
    }).catch((e: unknown) => {
      if (live) { setScopes([]); setSection(''); setTestId(''); setDetail(null); setItem(null); setHistory(null); setError(e instanceof Error ? e.message : 'Assessment scope unavailable') }
    })
    return () => { live = false }
  }, [accessToken, tick])
  useEffect(() => {
    if (!section) return
    let live = true
    setLoading(true); setList(null)
    getTests(accessToken, section, page * 50).then(data => { if (live) setList(data) })
      .catch((e: unknown) => { if (live) { setDetail(null); setItem(null); setError(e instanceof Error ? e.message : 'Unable to load tests') } })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [accessToken, section, page, tick])
  useEffect(() => {
    if (!testId) return
    let live = true
    setDetail(null); setHistory(null); setLoading(true)
    getTest(accessToken, testId).then(data => { if (live) setDetail(data) })
      .catch((e: unknown) => { if (live) { setItem(null); setError(e instanceof Error ? e.message : 'Unable to load assessment') } })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [accessToken, testId, tick])
  useEffect(() => {
    if (view !== 'history' || !testId) return
    let live = true
    getTestHistory(accessToken, testId).then(data => { if (live) setHistory(data) })
      .catch((e: unknown) => { if (live) setError(e instanceof Error ? e.message : 'Unable to load history') })
    return () => { live = false }
  }, [accessToken, view, testId, tick])

  async function act(work: () => Promise<void>, message: string) {
    if (busy) return
    const current = generation.current
    setBusy(true); setError(''); setSuccess('')
    try { await work(); if (current === generation.current) setSuccess(message) }
    catch (e) {
      if (current !== generation.current) return
      setError(e instanceof Error ? e.message : 'Assessment operation failed')
      if (e && typeof e === 'object' && 'status' in e && (e.status === 403 || e.status === 404)) { setDetail(null); setItem(null); setHistory(null) }
    } finally { if (current === generation.current) setBusy(false) }
  }
  async function inContext<T,>(work: Promise<T>): Promise<T> {
    const current = generation.current
    const result = await work
    if (current !== generation.current) throw new Error('Assessment context changed')
    return result
  }
  async function reload(id = testId) { const refreshed = await inContext(getTest(accessToken, id)); setDirty(false); setItem(null); setDetail(refreshed); setTick(n => n + 1) }
  function selectTest(test: FacultyTest) { if (!busy && canLeave()) { generation.current++; setTestId(test.test_id); setItem(null); setView('results'); setError('') } }
  async function save(data: TestInput, schedule: boolean) {
    await act(async () => {
      const saved = await inContext(editing && t ? updateTest(accessToken, t.test_id, { ...data, expected_version: t.version }) : createTest(accessToken, section, data))
      setDirty(false)
      setTestId(saved.test_id); setEditing(false); setView('results')
      if (schedule) await inContext(transitionTest(accessToken, saved, 'schedule'))
      setTick(n => n + 1)
    }, 'Assessment saved.')
  }
  const scopesForFilters = useMemo(() => scopes.map(s => ({ assignment_id: s.section_id, assigned_at: '', section_id: s.section_id,
    semester_id: s.semester_id ?? '', academic_year_id: s.academic_year_id ?? '', section: s, can_manage: s.can_manage })), [scopes])
  const availableViews = (Object.keys(labels) as View[]).filter(v => scope?.can_manage || !['create', 'import'].includes(v))
  const transitions = t ? ({ DRAFT: ['schedule'], SCHEDULED: ['start', 'complete'], ONGOING: ['complete'],
    COMPLETED: t.marks_state === 'DRAFT' ? ['submit'] : ['return_marks', 'publish'], PUBLISHED: ['lock'], LOCKED: [], CANCELLED: [] }[t.status]) : []
  const blocking = !detail || !detail.review.total || Boolean(detail.review.missing || detail.review.conflicts)

  return <div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="flex items-center gap-2 text-2xl font-bold"><ClipboardCheck aria-hidden="true" className="text-[#ffc72c]" />Tests &amp; Examinations</h1><p className="mt-1 text-sm text-slate-400">Schedule assessments, record marks and publish reviewed results.</p></div><button className={button} disabled={busy} onClick={() => { if (canLeave()) { setError(''); setTick(n => n + 1) } }}><RefreshCw aria-hidden="true" className="mr-2 inline h-4 w-4" />Refresh</button></div>
    {error ? <p role="alert" className="rounded-lg border border-red-800 bg-red-500/10 p-3 text-sm text-red-300">{error}</p> : null}
    {success ? <p role="status" className="rounded-lg border border-emerald-800 p-3 text-sm text-emerald-300">{success}</p> : null}
    {scopes.length ? <section className={surface}><AttendanceAcademicFilters scopes={scopesForFilters} selectedId={section} onChange={id => { if (busy) return; if (canLeave()) { generation.current++; setSection(id); setTestId(''); setDetail(null); setItem(null); setHistory(null); setPage(0); setView('overview'); setError('') } }} /><p className="mt-3 text-xs text-slate-400">{scope?.can_manage ? 'Teaching scope · Assessment creation is available. Existing tests require their owner.' : 'Responsibility monitoring · Read-only access within your assigned scope.'}</p></section> : !loading ? <section className={`${surface} py-16 text-center`}><h2 className="text-lg font-semibold">No authorized assessment scopes</h2><p className="mt-2 text-sm text-slate-400">An active teaching assignment or mapped monitoring responsibility is required.</p></section> : null}
    {scopes.length ? <nav aria-label="Assessment workspace" className="flex flex-wrap gap-2">{availableViews.map(v => <button key={v} className={`${button} ${view === v ? 'border-amber-500 text-amber-300' : ''}`} aria-current={view === v ? 'page' : undefined} disabled={busy} onClick={() => navigate(v)}>{labels[v]}</button>)}</nav> : null}
    {loading ? <p role="status" className="py-8 text-center text-slate-400">Loading assessments…</p> : null}
    {view === 'overview' && list ? <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{[['upcoming', 'Upcoming tests'], ['draft', 'Draft tests'], ['completed', 'Completed tests'], ['pending_marks', 'Pending mark entry'], ['published', 'Published results'], ['locked', 'Locked results']].map(([key, label]) => <AttendanceMetric key={key} label={label} value={list.overview[key] ?? 0} icon="calendar" tone="yellow" />)}</div> : null}
    {(view === 'overview' || view === 'tests') && list ? <section className={`${surface} space-y-4`}><div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Assessments in this subject / section</h2>{scope?.can_manage ? <button className={button} onClick={() => navigate('create')}><Plus aria-hidden="true" className="mr-1 inline h-4 w-4" />Create assessment</button> : null}</div>{list.items.length ? <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="text-xs text-slate-400"><tr>{['Assessment', 'Date / time', 'Maximum', 'Lifecycle', 'Marks', 'Review'].map(h => <th scope="col" className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{list.items.map(test => <tr className="border-t border-[#263d55]" key={test.test_id}><td className="p-2 font-medium">{test.title}<p className="text-xs text-slate-500">{types.find(type => type.code === test.test_type)?.name ?? test.test_type}</p></td><td>{test.scheduled_date ?? 'Unscheduled'}<p className="text-xs text-slate-500">{test.start_time ?? ''}{test.end_time ? `–${test.end_time}` : ''}</p></td><td>{test.max_marks}</td><td>{test.status}</td><td>{test.marks_state}</td><td><button className={button} disabled={busy} onClick={() => selectTest(test)}>Open {test.title}</button></td></tr>)}</tbody></table></div> : <p role="status" className="py-12 text-center text-slate-400">No tests yet for this subject and section.</p>}<div className="flex justify-end gap-3"><button className={button} disabled={!page} onClick={() => setPage(page - 1)}>Previous tests</button><span className="self-center text-xs">{list.total} tests · Page {page + 1}</span><button className={button} disabled={(page + 1) * 50 >= list.total} onClick={() => setPage(page + 1)}>Next tests</button></div></section> : null}
    {view === 'create' && scope?.can_manage ? <TestForm key={editing ? t?.test_id : 'new'} types={types} initial={editing ? t : undefined} busy={busy} onDirty={() => setDirty(true)} onSave={(data, schedule) => { void save(data, schedule) }} onCancel={() => navigate('tests')} /> : null}
    {['marks', 'results', 'import', 'history'].includes(view) && !testId ? <p role="status" className={`${surface} text-slate-400`}>Open an assessment from My Tests to continue.</p> : null}
    {t && ['marks', 'results', 'import', 'history'].includes(view) ? <section className={`${surface} space-y-3`}><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">{t.title}</h2><p className="text-xs text-slate-400">{t.section?.course.name} · Section {t.section?.code} · {t.scheduled_date ?? 'Unscheduled'} · {t.status} · {t.marks_state} marks</p></div>{t.can_manage && (t.can_edit_metadata ?? (['DRAFT', 'SCHEDULED'].includes(t.status) && !detail.rows.some(r => r.mark_status !== 'missing'))) ? <button className={button} disabled={busy} onClick={() => { if (canLeave()) { setEditing(true); setView('create') } }}>Edit assessment</button> : null}</div>{t.description ? <p className="whitespace-pre-wrap text-sm text-slate-400">{t.description}</p> : null}{t.can_manage ? <div className="flex flex-wrap gap-3">{transitions.map(action => <button key={action} className={button} disabled={busy || unsaved || (['submit', 'publish'].includes(action) && blocking)} onClick={() => { void act(async () => { await inContext(transitionTest(accessToken, t, action)); await reload() }, `Assessment ${action.replace('_', ' ')} completed.`) }}>{({ schedule: 'Schedule test', start: 'Start test', complete: 'Complete test', submit: 'Submit reviewed marks', return_marks: 'Return marks to draft', publish: 'Publish results', lock: 'Lock results' } as Record<string, string>)[action]}</button>)}{!['PUBLISHED', 'LOCKED', 'CANCELLED'].includes(t.status) ? <button className={`${button} text-red-300`} disabled={busy || unsaved} onClick={() => { if (window.confirm('Cancel this assessment? Its history will be retained.')) void act(async () => { await inContext(transitionTest(accessToken, t, 'cancel')); await reload() }, 'Assessment cancelled.') }}>Cancel test</button> : null}</div> : <p className="text-sm text-slate-400">Monitoring access · This assessment is read-only.</p>}</section> : null}
    {detail && (view === 'marks' || view === 'results') ? <>{view === 'results' ? <section className={`${surface} space-y-3`}><h2 className="font-semibold">Result review</h2><div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">{Object.entries(detail.review).map(([key, value]) => <div key={key} className="rounded border border-[#263d55] p-3"><p className="text-xs text-slate-400">{key.replaceAll('_', ' ')}</p><p className="mt-1 font-semibold">{value === null ? '—' : key === 'average_percentage' ? `${value.toFixed(2)}%` : value}</p></div>)}</div><p className="text-xs text-slate-400">Statistics use recorded present scores. Absent/exempt/missing are separate. Pass/fail uses the assessment's passing marks.</p>{blocking ? <p className="text-sm text-amber-300">Resolve missing marks and identity conflicts before submission or publication.</p> : null}</section> : null}<MarksEditor key={`${detail.test.test_id}:${detail.test.version}`} detail={detail} busy={busy} onDirty={setDirty} onSave={(rows, reason) => { void act(async () => { await inContext(saveTestMarks(accessToken, detail.test, rows.map(({ roster_id, mark_status, scored_marks, remarks }) => ({ roster_id, mark_status, scored_marks, remarks })), reason)); await reload() }, reason ? 'Audited correction saved. Result remains locked.' : 'Marks saved atomically.') }} /></> : null}
    {view === 'import' && t ? <>{t.can_manage && t.status === 'COMPLETED' && t.marks_state === 'DRAFT' ? <section className={`${surface} space-y-3`}><h2 className="font-semibold">Upload marks</h2><p className="text-sm text-slate-400">CSV, XLSX or XLS · 10 MB · up to 500 rows · values only.</p><p className="text-xs text-slate-400">Columns: register_number, mark_status, scored_marks. Optional: university_roll_number, remarks. Use present, absent, exempt or not_attempted; non-present marks stay empty.</p><label className="block text-sm">Choose marks spreadsheet<input className={field} type="file" accept=".csv,.xlsx,.xls" disabled={busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (file) void act(async () => { setItem(await inContext(uploadTestMarks(accessToken, t.test_id, file))) }, 'File validated. Review before import.') }} /></label></section> : <p className={`${surface} text-sm text-slate-400`}>Import requires your completed assessment with draft marks. Prior reviews are available in History.</p>}{item ? <MarksImportReview key={item.updated_at} item={item} canManage={Boolean(t.can_manage) && t.status === 'COMPLETED' && t.marks_state === 'DRAFT'} busy={busy} onCorrect={(row, data) => { void act(async () => { setItem(await inContext(correctTestImport(accessToken, item, row, data))) }, 'Import row revalidated.') }} onCommit={() => { void act(async () => { await inContext(commitTestImport(accessToken, item, t)); const reviewed = await inContext(getTestImport(accessToken, item.import_id)); await reload(); setItem(reviewed) }, 'Reviewed marks imported atomically.') }} /> : null}</> : null}
    {view === 'history' && history ? <section className={`${surface} space-y-4`}><h2 className="font-semibold">Import &amp; assessment history</h2>{!history.imports.length && !history.events.length ? <p className="text-sm text-slate-400">No history yet.</p> : null}{history.imports.map(i => <div key={i.import_id} className="flex flex-wrap justify-between gap-3 rounded border border-[#263d55] p-3 text-sm"><div>{i.original_filename} · {i.status}<p className="text-xs text-slate-500">{i.created_at} · Uploader {i.uploaded_by} · {i.summary.total_rows ?? 0} rows</p></div><button className={button} disabled={busy} onClick={() => { void act(async () => { setItem(await inContext(getTestImport(accessToken, i.import_id))); setView('import') }, '') }}>Review import</button></div>)}{history.events.map((event, index) => <details key={`${event.performed_at}:${index}`} className="rounded border border-[#263d55] p-3 text-sm"><summary className="cursor-pointer">{event.action} · {new Date(event.performed_at).toLocaleString()}</summary><p className="mt-2 text-xs text-slate-500">Actor {event.actor_user_id}</p><pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-400">{JSON.stringify(event.record_data, null, 2)}</pre></details>)}</section> : null}
  </div>
}

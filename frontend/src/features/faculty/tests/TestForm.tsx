import { useRef } from 'react'
import type { FacultyTest, TestInput } from '../../../services/facultyTestsApi.ts'

export const field = 'mt-1 w-full rounded-md border border-[#263d55] bg-[#091725] px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-50'
export const button = 'rounded-md border border-[#304862] px-4 py-2 text-sm text-slate-200 hover:bg-[#182d43] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
export const surface = 'rounded-xl border border-[#1e3348] bg-[#0d1c2c] p-5'

export default function TestForm({ types, initial, busy, onSave, onCancel, onDirty }: {
  types: Array<{ code: string; name: string }>; initial?: FacultyTest; busy: boolean
  onSave: (data: TestInput, schedule: boolean) => void; onCancel: () => void; onDirty: () => void
}) {
  const schedule = useRef(false)
  return <form className={`${surface} space-y-5`} onChange={onDirty} onSubmit={(e) => {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const text = (key: string) => String(data.get(key) ?? '').trim() || null
    const number = (key: string) => text(key) === null ? null : Number(text(key))
    onSave({ title: text('title') ?? '', test_type: text('test_type') ?? '', description: text('description'),
      max_marks: number('max_marks') ?? 0, passing_marks: number('passing_marks'), scheduled_date: text('scheduled_date'),
      start_time: text('start_time'), end_time: text('end_time'), duration_minutes: number('duration_minutes') }, schedule.current)
  }}>
    <h2 className="text-lg font-semibold">{initial ? 'Edit assessment' : 'Create assessment'}</h2>
    <p className="text-sm text-slate-400">The selected subject and section define the academic scope. Dates must be within that semester.</p>
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-xs text-slate-400">Title<input className={field} disabled={busy} name="title" required maxLength={160} defaultValue={initial?.title} /></label>
      <label className="text-xs text-slate-400">Test type<select className={field} disabled={busy} name="test_type" required defaultValue={initial?.test_type ?? types[0]?.code}>{types.map(t => <option key={t.code} value={t.code}>{t.name}</option>)}</select></label>
      <label className="text-xs text-slate-400">Maximum marks<input className={field} disabled={busy} name="max_marks" type="number" min="0.01" max="999999.99" step="0.01" required defaultValue={initial?.max_marks ?? 100} /></label>
      <label className="text-xs text-slate-400">Passing marks (optional)<input className={field} disabled={busy} name="passing_marks" type="number" min="0" max="999999.99" step="0.01" defaultValue={initial?.passing_marks ?? ''} /></label>
      <label className="text-xs text-slate-400">Date<input className={field} disabled={busy} name="scheduled_date" type="date" defaultValue={initial?.scheduled_date ?? ''} /></label>
      <label className="text-xs text-slate-400">Duration in minutes (optional)<input className={field} disabled={busy} name="duration_minutes" type="number" min="1" max="1440" defaultValue={initial?.duration_minutes ?? ''} /></label>
      <label className="text-xs text-slate-400">Start time (optional)<input className={field} disabled={busy} name="start_time" type="time" defaultValue={initial?.start_time ?? ''} /></label>
      <label className="text-xs text-slate-400">End time (optional)<input className={field} disabled={busy} name="end_time" type="time" defaultValue={initial?.end_time ?? ''} /></label>
    </div>
    <label className="block text-xs text-slate-400">Description / instructions<textarea className={field} disabled={busy} name="description" rows={3} maxLength={4000} defaultValue={initial?.description ?? ''} /></label>
    <div className="flex flex-wrap gap-3"><button className={`${button} border-amber-500 text-amber-300`} disabled={busy || !types.length} type="submit" onClick={() => { schedule.current = false }}>{initial ? 'Save changes' : 'Save draft'}</button>{!initial || initial.status === 'DRAFT' ? <button className={button} disabled={busy || !types.length} type="submit" onClick={() => { schedule.current = true }}>Save and schedule</button> : null}<button type="button" className={button} disabled={busy} onClick={onCancel}>Cancel</button></div>
  </form>
}

import { useState } from 'react'
import type { MarksDetail, MarkRow, MarkStatus } from '../../../services/facultyTestsApi.ts'
import { button, field, surface } from './TestForm.tsx'

export default function MarksEditor({ detail, busy, onSave, onDirty }: {
  detail: MarksDetail; busy: boolean; onSave: (rows: MarkRow[], reason?: string) => void; onDirty: (dirty: boolean) => void
}) {
  const [rows, setRows] = useState(detail.rows)
  const [changed, setChanged] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [correction, setCorrection] = useState(false)
  const [reason, setReason] = useState('')
  const editable = Boolean(detail.test.can_manage) && ((detail.test.status === 'COMPLETED' && detail.test.marks_state === 'DRAFT') || correction)
  const visible = rows.filter(r => `${r.register_number} ${r.student_name} ${r.university_roll_number ?? ''}`.toLowerCase().includes(search.toLowerCase()))
  function canEdit(row: MarkRow) {
    return editable && !busy && row.reconciliation_state !== 'CONFLICT' && (correction || row.roster_status !== 'INACTIVE')
      && (changed.size < 500 || changed.has(row.roster_id))
  }
  function update(id: string, patch: Partial<MarkRow>) {
    setRows(current => current.map(r => r.roster_id === id ? { ...r, ...patch } : r))
    setChanged(current => new Set(current).add(id)); onDirty(true)
  }
  const invalid = rows.some(r => changed.has(r.roster_id) && (r.mark_status === 'present' &&
    (r.scored_marks === null || !Number.isFinite(r.scored_marks) || r.scored_marks < 0 || r.scored_marks > detail.test.max_marks || Math.abs(r.scored_marks * 100 - Math.round(r.scored_marks * 100)) > 0.00001)))
  return <section className={`${surface} space-y-4`}><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">Marks &amp; results</h2><p className="text-xs text-slate-400">Maximum {detail.test.max_marks} · {detail.test.marks_state} marks · {detail.test.status}</p></div>{detail.test.can_manage && detail.test.status === 'LOCKED' && !correction ? <button className={button} onClick={() => setCorrection(true)}>Request a controlled correction</button> : null}</div>
    {correction ? <label className="block text-sm text-amber-300">Correction reason (at least 10 characters)<textarea className={field} disabled={busy} value={reason} onChange={e => { setReason(e.target.value); onDirty(true) }} maxLength={1000} /><span className="text-xs">Previous and corrected values are retained in the audit history. The result stays locked.</span></label> : null}
    {!editable ? <p className="text-sm text-slate-400">Read-only marks. {detail.test.status === 'LOCKED' ? 'Normal editing is locked.' : 'Marks entry requires your completed assessment with draft marks.'}</p> : null}
    <label className="block max-w-sm text-xs text-slate-400">Find student<input className={field} value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} /></label>
    {invalid ? <p role="alert" className="text-sm text-red-300">Present requires marks from 0 to {detail.test.max_marks}, with at most two decimal places.</p> : null}
    {changed.size >= 500 ? <p role="status" className="text-sm text-amber-300">Save these 500 rows before editing more students.</p> : null}
    <div className="overflow-x-auto"><table className="w-full min-w-[950px] text-left text-sm"><caption className="sr-only">Assessment marks roster</caption><thead className="text-xs text-slate-400"><tr>{['Student', 'Register number', 'University roll', 'Status', 'Marks', 'Percentage / result', 'Teacher remarks'].map(h => <th scope="col" className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{visible.slice(page * 25, page * 25 + 25).map(r => <tr className="border-t border-[#263d55]" key={r.roster_id}><td className="p-2">{r.student_name}<p className="text-xs text-slate-500">{r.roster_status}{r.reconciliation_state === 'CONFLICT' ? ' · Identity conflict' : ''}</p></td><td>{r.register_number}</td><td>{r.university_roll_number ?? '—'}</td><td><select aria-label={`Status for ${r.register_number}`} className={field} disabled={!canEdit(r)} value={r.mark_status} onChange={e => { const status = e.target.value as MarkStatus; update(r.roster_id, { mark_status: status, scored_marks: status === 'present' ? r.scored_marks : null }) }}>{['missing', 'present', 'absent', 'exempt', 'not_attempted'].map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}</select></td><td><input aria-label={`Marks for ${r.register_number}`} className={`${field} w-28`} type="number" min={0} max={detail.test.max_marks} step="0.01" value={r.scored_marks ?? ''} disabled={!canEdit(r) || r.mark_status !== 'present'} onChange={e => update(r.roster_id, { scored_marks: e.target.value === '' ? null : Number(e.target.value) })} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); const inputs = Array.from(e.currentTarget.closest('tbody')?.querySelectorAll<HTMLInputElement>('input[type="number"]:not(:disabled)') ?? []); inputs[inputs.indexOf(e.currentTarget) + 1]?.focus() } }} /></td><td className="p-2">{r.percentage === null ? '—' : `${r.percentage}%`}{r.outcome ? ` · ${r.outcome}` : ''}</td><td><input className={field} aria-label={`Remarks for ${r.register_number}`} value={r.remarks ?? ''} disabled={!canEdit(r)} maxLength={1000} onChange={e => update(r.roster_id, { remarks: e.target.value || null })} /></td></tr>)}</tbody></table></div>
    {!rows.length ? <p role="status" className="py-8 text-center text-slate-400">No students in the existing authorized roster. Add students through the roster workflow first.</p> : null}
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-amber-300">{changed.size ? `${changed.size} unsaved rows` : 'All changes saved'} · Absent, exempt and missing remain distinct from zero.</p><div className="flex items-center gap-2"><button className={button} disabled={!page} onClick={() => setPage(page - 1)}>Previous students</button><span className="text-xs">Page {page + 1}</span><button className={button} disabled={(page + 1) * 25 >= visible.length} onClick={() => setPage(page + 1)}>Next students</button></div></div>
    {editable ? <button className={`${button} border-amber-500 text-amber-300`} disabled={busy || !changed.size || changed.size > 500 || invalid || (correction && reason.trim().length < 10)} onClick={() => onSave(rows.filter(r => changed.has(r.roster_id)), correction ? reason : undefined)}>{busy ? 'Saving…' : correction ? 'Save audited correction' : 'Save marks'}</button> : null}
  </section>
}

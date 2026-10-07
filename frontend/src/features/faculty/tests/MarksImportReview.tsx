import { useState } from 'react'
import type { TestImport } from '../../../services/facultyTestsApi.ts'
import { button, field, surface } from './TestForm.tsx'

export default function MarksImportReview({ item, canManage, busy, onCorrect, onCommit }: {
  item: TestImport; canManage: boolean; busy: boolean; onCorrect: (row: number, data: Record<string, string>) => void; onCommit: () => void
}) {
  const [editing, setEditing] = useState<number | null>(null)
  const [data, setData] = useState<Record<string, string>>({})
  const [page, setPage] = useState(0)
  const readonly = !canManage || item.status === 'IMPORTED'
  const blocked = item.rows.some(r => r.errors.length > 0)
  return <section className={`${surface} space-y-4`}><h2 className="text-lg font-semibold">Import review · {item.original_filename}</h2><p className="text-sm text-slate-400">{item.status === 'IMPORTED' ? 'Import completed. This review is read-only.' : 'Review identities, marks and warnings before explicit import.'}</p>
    <div className="flex flex-wrap gap-4 text-xs">{Object.entries(item.summary).map(([label, value]) => <span key={label}>{label.replace('_', ' ')}: <strong>{value}</strong></span>)}</div>
    <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="text-xs text-slate-400"><tr>{['Row / register', 'Marks / status', 'Validation', 'Issues', 'Correction'].map(h => <th scope="col" key={h} className="p-2">{h}</th>)}</tr></thead><tbody>{item.rows.slice(page * 25, page * 25 + 25).map(r => <tr className="border-t border-[#263d55]" key={r.row_number}><td className="p-2">{r.row_number} · {r.normalized_data.register_number}</td><td>{r.normalized_data.scored_marks || '—'} · {r.normalized_data.mark_status}</td><td className={r.errors.length ? 'text-red-300' : r.warnings.length ? 'text-amber-300' : 'text-emerald-300'}>{r.validation_status}{r.warnings.length ? ' · WARNING' : ''}</td><td className="max-w-md p-2">{[...r.errors, ...r.warnings].join('; ') || 'Valid'}</td><td>{!readonly ? <button className={button} disabled={busy} onClick={() => { setEditing(r.row_number); setData(r.raw_data) }}>Correct row {r.row_number}</button> : 'Read-only'}</td></tr>)}</tbody></table></div>
    {editing !== null ? <form className="grid gap-3 sm:grid-cols-2" onSubmit={e => { e.preventDefault(); onCorrect(editing, data); setEditing(null) }}>{['register_number', 'university_roll_number', 'scored_marks', 'mark_status', 'remarks'].map(key => <label key={key} className="text-xs text-slate-400">{key.replaceAll('_', ' ')}<input className={field} value={data[key] ?? ''} onChange={e => setData({ ...data, [key]: e.target.value })} /></label>)}<div className="flex gap-3"><button className={button} disabled={busy}>Revalidate row</button><button className={button} type="button" onClick={() => setEditing(null)}>Cancel correction</button></div></form> : null}
    <div className="flex flex-wrap justify-between gap-3">{!readonly ? <button className={`${button} border-amber-500 text-amber-300`} disabled={blocked || busy || editing !== null} onClick={onCommit}>{busy ? 'Importing…' : 'Import reviewed marks'}</button> : <p className="text-sm text-slate-400">Read-only review</p>}<div className="flex gap-2"><button className={button} disabled={!page} onClick={() => setPage(page - 1)}>Previous import rows</button><button className={button} disabled={(page + 1) * 25 >= item.rows.length} onClick={() => setPage(page + 1)}>Next import rows</button></div></div>
  </section>
}

import type { AcademicCatalogue, AcademicRecord } from '../../../types/academicSetup.ts'
import { academicButtonClass } from './forms/academicFormControls.ts'
import { academicRecordId } from './academicSetupForm.ts'
import { academicRecordContext, academicRecordLabel } from './academicSetupLabels.ts'

interface Props {
  records: AcademicRecord[]
  catalogue: AcademicCatalogue
  manageable: boolean
  busy: boolean
  onEdit: (record: AcademicRecord) => void
  onToggle: (record: AcademicRecord) => void
}
export default function AcademicSetupRecords({ records, catalogue, manageable, busy, onEdit, onToggle }: Props) {
  if (!records.length) return <p className="text-sm text-slate-400">No records yet.</p>
  return (
    <ul className="space-y-3" aria-label="Academic records">
      {records.map((record) => {
        const label = 'name' in record ? record.name : academicRecordLabel(record, catalogue)
        return (
          <li
            key={academicRecordId(record)}
            className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-slate-700 bg-slate-800 p-4"
          >
            <div className="space-y-1">
              <h3 className="font-semibold text-white">{label}</h3>
              <p className="text-sm text-slate-300">
                {'code' in record ? `${record.code} ? ` : ''}
                {record.is_active ? 'Active' : 'Inactive'}
                {'is_current' in record && record.is_current ? ' ? Current' : ''}
              </p>
              <p className="text-sm text-slate-400">{academicRecordContext(record, catalogue)}</p>
              {'description' in record && record.description && (
                <p className="text-sm text-slate-400">{record.description}</p>
              )}
              {'degree_type' in record && (
                <p className="text-sm text-slate-400">
                  {record.degree_type} ? {record.duration_years} years
                  {record.total_credits === null ? '' : ` ? ${record.total_credits} credits`}
                </p>
              )}
              {'credits' in record && (
                <p className="text-sm text-slate-400">
                  {record.credits === null ? 'Credits unspecified' : `${record.credits} credits`} ? Lecture{' '}
                  {record.lecture_hours ?? '?'} / Tutorial {record.tutorial_hours ?? '?'} / Practical{' '}
                  {record.practical_hours ?? '?'}
                </p>
              )}
              {'start_date' in record && (
                <p className="text-sm text-slate-400">
                  {record.start_date} to {record.end_date}
                </p>
              )}
              {'capacity' in record && (
                <p className="text-sm text-slate-400">Capacity: {record.capacity ?? 'Unspecified'}</p>
              )}
            </div>
            {manageable && (
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onEdit(record)}
                  aria-label={`Edit ${label}`}
                  className={academicButtonClass}
                >
                  Edit
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onToggle(record)}
                  aria-label={`${record.is_active ? 'Deactivate' : 'Activate'} ${label}`}
                  className={academicButtonClass}
                >
                  {record.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

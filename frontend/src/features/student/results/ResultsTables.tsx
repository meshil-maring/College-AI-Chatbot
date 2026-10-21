import type { StudentAcademicResultRecord, StudentTestResultRecord } from '../../../types/student.ts'
import { NOT_PROVIDED } from '../shared/SectionState.tsx'
import { formatDate, formatLabel, formatNumber, formatPercent, formatScore, formatText } from '../shared/studentFormat.ts'
export function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 truncate text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

export function AcademicResultsTable({ records }: { records: StudentAcademicResultRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[36rem] text-left text-sm">
        <caption className="sr-only">Your published examination results</caption>
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">
              Result type
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Credits earned
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Credits max
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              SGPA
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              CGPA
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Status
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Issued
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {records.map((record, index) => (
            <tr key={index}>
              <td className="max-w-[10rem] truncate px-3 py-2 text-slate-200">{formatLabel(record?.result_type)}</td>
              <td className="max-w-[7rem] truncate px-3 py-2 text-slate-200 tabular-nums">
                {formatNumber(record?.total_credits_earned)}
              </td>
              <td className="max-w-[7rem] truncate px-3 py-2 text-slate-300 tabular-nums">
                {formatNumber(record?.total_credits_max)}
              </td>
              <td className="max-w-[6rem] truncate px-3 py-2 text-slate-200 tabular-nums">
                {formatNumber(record?.sgpa)}
              </td>
              <td className="max-w-[6rem] truncate px-3 py-2 text-slate-200 tabular-nums">
                {formatNumber(record?.cgpa)}
              </td>
              <td className="max-w-[8rem] truncate px-3 py-2 text-slate-300">{formatLabel(record?.status)}</td>
              <td className="max-w-[9rem] truncate px-3 py-2 text-slate-400">
                {formatDate(typeof record?.issued_at === 'string' ? record.issued_at : null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function TestScoresTable({ records }: { records: StudentTestResultRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[32rem] text-left text-sm">
        <caption className="sr-only">Your published test scores</caption>
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">
              Test
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Course
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Marks
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Grade
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              Conducted
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {records.map((record, index) => (
            <tr key={index}>
              <td className="max-w-[12rem] break-words px-3 py-2 text-slate-200">{formatText(record?.test_name)}</td>
              <td className="max-w-[12rem] break-words px-3 py-2 text-slate-300">
                {courseLabel(record?.course_name, record?.course_code)}
              </td>
              <td className="max-w-[8rem] truncate px-3 py-2 text-slate-200 tabular-nums">
                {record.mark_status && record.mark_status !== 'present'
                  ? formatLabel(record.mark_status)
                  : formatScore(record?.scored_marks, record?.max_marks)}
                {record.outcome ? (
                  <span className="block text-xs text-slate-300">{formatLabel(record.outcome)}</span>
                ) : null}
                {typeof record?.percentage === 'number' && Number.isFinite(record.percentage) ? (
                  <span className="block text-xs text-slate-500">{formatPercent(record.percentage)}</span>
                ) : null}
              </td>
              <td className="max-w-[6rem] truncate px-3 py-2 text-slate-200">{formatText(record?.letter_grade)}</td>
              <td className="max-w-[9rem] truncate px-3 py-2 text-slate-400">
                {formatDate(typeof record?.conducted_at === 'string' ? record.conducted_at : null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function courseLabel(courseName: unknown, courseCode: unknown): string {
  if (typeof courseName === 'string' && courseName.trim() !== '') return courseName
  if (typeof courseCode === 'string' && courseCode.trim() !== '') return courseCode
  return NOT_PROVIDED
}

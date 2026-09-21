/** Phase 6.16 — Results summary (read-only; no invented aggregates). */

import type { StudentOwnResults, StudentOwnTestResults } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock, NOT_PROVIDED } from './SectionState.tsx'
import { formatDate, formatLabel, formatNumber, formatPercent, formatScore } from './studentFormat.ts'

const EMPTY_MESSAGE = 'No examination results are available yet.'

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

export default function ResultsPanel({
  results,
  testResults,
  compact = false,
}: {
  results: StudentResourceState<StudentOwnResults>
  testResults: StudentResourceState<StudentOwnTestResults>
  compact?: boolean
}) {
  const loading =
    results.status === 'loading' || results.status === 'idle' ||
    testResults.status === 'loading' || testResults.status === 'idle'
  if (loading) return <LoadingBlock label="Loading your results…" />
  if (results.status === 'error' || testResults.status === 'error') {
    const failed = results.status === 'error' ? results : testResults
    return <ErrorBlock message={failed.error ?? 'Unable to load results.'} onRetry={failed.reload} />
  }
  const academicRecords = results.data?.records ?? []
  const testRecords = testResults.data?.records ?? []
  const academicAvailable = results.data?.summary.records_available ?? false
  const testAvailable = testResults.data?.summary.records_available ?? false
  if (!academicAvailable && !testAvailable && academicRecords.length === 0 && testRecords.length === 0) {
    return <EmptyBlock message={EMPTY_MESSAGE} />
  }
  const latestAcademic = academicRecords[0] ?? null
  const latestTests = compact ? testRecords.slice(0, 3) : testRecords
  return (
    <>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Figure label="Academic results" value={String(results.data?.summary.total_results ?? academicRecords.length)} />
        <Figure label="Test scores" value={String(testResults.data?.summary.total_results ?? testRecords.length)} />
        <Figure label="Latest SGPA" value={latestAcademic?.sgpa !== null && latestAcademic?.sgpa !== undefined ? String(latestAcademic.sgpa) : NOT_PROVIDED} />
      </dl>
      {latestAcademic ? (
        <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">Latest result type</dt>
            <dd className="mt-0.5 text-sm font-medium text-white">{formatLabel(latestAcademic.result_type)}</dd>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">Issued</dt>
            <dd className="mt-0.5 text-sm font-medium text-white">{formatDate(latestAcademic.issued_at)}</dd>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">CGPA</dt>
            <dd className="mt-0.5 text-sm font-medium text-white">{formatNumber(latestAcademic.cgpa)}</dd>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">Status</dt>
            <dd className="mt-0.5 text-sm font-medium text-white">{formatLabel(latestAcademic.status)}</dd>
          </div>
        </dl>
      ) : null}
      {latestTests.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Your recent test scores</caption>
            <thead className="bg-slate-800 text-xs text-slate-400">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">Test</th>
                <th scope="col" className="px-3 py-2 font-medium">Course</th>
                <th scope="col" className="px-3 py-2 font-medium">Score</th>
                <th scope="col" className="px-3 py-2 font-medium">Grade</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {latestTests.map((record, index) => (
                <tr key={`${record.test_name ?? 'test'}-${index}`}>
                  <td className="px-3 py-2 text-slate-200">{record.test_name?.trim() || NOT_PROVIDED}</td>
                  <td className="px-3 py-2 text-slate-300">{record.course_name?.trim() || record.course_code?.trim() || NOT_PROVIDED}</td>
                  <td className="px-3 py-2 text-slate-200 tabular-nums">
                    {formatScore(record.scored_marks, record.max_marks)}
                    {record.percentage !== null && record.percentage !== undefined ? (
                      <span className="block text-xs text-slate-500">{formatPercent(record.percentage)}</span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-slate-200">{record.letter_grade?.trim() || NOT_PROVIDED}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  )
}

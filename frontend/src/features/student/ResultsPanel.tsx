/** Phase 6.16.1 — Results summary (read-only; no invented aggregates). */

import type { StudentOwnResults, StudentOwnTestResults } from '../../types/student.ts'
import type { StudentResourceState } from './useStudentResource.ts'
import { EmptyBlock, ErrorBlock, LoadingBlock, NOT_PROVIDED } from './SectionState.tsx'
import { formatDate, formatLabel, formatNumber, formatPercent, formatScore, formatText, isDisplayableNumber } from './studentFormat.ts'

const EMPTY_MESSAGE = 'No examination results are available yet.'

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 truncate text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}

function formatCount(value: unknown, fallback: number): string {
  if (isDisplayableNumber(value)) return String(value)
  return String(fallback)
}

function courseLabel(courseName: unknown, courseCode: unknown): string {
  if (typeof courseName === 'string' && courseName.trim() !== '') return courseName
  if (typeof courseCode === 'string' && courseCode.trim() !== '') return courseCode
  return NOT_PROVIDED
}

export default function ResultsPanel({
  results,
  testResults,
}: {
  results: StudentResourceState<StudentOwnResults>
  testResults: StudentResourceState<StudentOwnTestResults>
  compact?: boolean
}) {
  const loading =
    results.status === 'loading' || results.status === 'idle' ||
    testResults.status === 'loading' || testResults.status === 'idle'
  if (loading) return <LoadingBlock label="Loading your results…" />
  if (results.status === 'error' && testResults.status === 'error') {
    return <ErrorBlock message={results.error ?? 'Unable to load results.'} onRetry={results.reload} />
  }
  const rawAcademic = results.status === 'loaded' ? results.data?.records : undefined
  const rawTests = testResults.status === 'loaded' ? testResults.data?.records : undefined
  const academicRecords = Array.isArray(rawAcademic) ? rawAcademic : []
  const testRecords = Array.isArray(rawTests) ? rawTests : []
  const academicAvailable =
    results.status === 'loaded' ? results.data?.summary.records_available === true : false
  const testAvailable =
    testResults.status === 'loaded' ? testResults.data?.summary.records_available === true : false
  if (
    results.status === 'loaded' &&
    testResults.status === 'loaded' &&
    !academicAvailable && !testAvailable &&
    academicRecords.length === 0 && testRecords.length === 0
  ) {
    return <EmptyBlock message={EMPTY_MESSAGE} />
  }
  if (academicRecords.length === 0 && testRecords.length === 0) {
    const failed = results.status === 'error' ? results : testResults
    return <ErrorBlock message={failed.error ?? 'Unable to load results.'} onRetry={failed.reload} />
  }
  const latestAcademic = academicRecords.length > 0 ? (academicRecords[0] ?? null) : null
  const latestTests = testRecords
  return (
    <>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Figure label="Academic results" value={formatCount(results.status === 'loaded' ? results.data?.summary.total_results : undefined, academicRecords.length)} />
        <Figure label="Test scores" value={formatCount(testResults.status === 'loaded' ? testResults.data?.summary.total_results : undefined, testRecords.length)} />
        <Figure
          label="Latest SGPA"
          value={latestAcademic !== null && isDisplayableNumber(latestAcademic.sgpa) ? String(latestAcademic.sgpa) : NOT_PROVIDED}
        />
      </dl>
      {results.status === 'error' ? (
        <div className="mt-3">
          <ErrorBlock message={results.error ?? 'Unable to load results.'} onRetry={results.reload} />
        </div>
      ) : null}
      {testResults.status === 'error' ? (
        <div className="mt-3">
          <ErrorBlock message={testResults.error ?? 'Unable to load results.'} onRetry={testResults.reload} />
        </div>
      ) : null}
      {latestAcademic ? (
        <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">Latest result type</dt>
            <dd className="mt-0.5 break-words text-sm font-medium text-white">{formatLabel(latestAcademic.result_type)}</dd>
          </div>
          <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">Issued</dt>
            <dd className="mt-0.5 break-words text-sm font-medium text-white">
              {formatDate(typeof latestAcademic.issued_at === 'string' ? latestAcademic.issued_at : null)}
            </dd>
          </div>
          <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">CGPA</dt>
            <dd className="mt-0.5 break-words text-sm font-medium text-white">{formatNumber(latestAcademic.cgpa)}</dd>
          </div>
          <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
            <dt className="text-xs text-slate-400">Status</dt>
            <dd className="mt-0.5 break-words text-sm font-medium text-white">{formatLabel(latestAcademic.status)}</dd>
          </div>
        </dl>
      ) : null}
      {latestTests.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full min-w-[32rem] text-left text-sm">
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
                <tr key={`${typeof record?.test_name === 'string' ? record.test_name : 'test'}-${index}`}>
                  <td className="max-w-[10rem] truncate px-3 py-2 text-slate-200">{formatText(record?.test_name)}</td>
                  <td className="max-w-[10rem] truncate px-3 py-2 text-slate-300">{courseLabel(record?.course_name, record?.course_code)}</td>
                  <td className="max-w-[8rem] truncate px-3 py-2 text-slate-200 tabular-nums">
                    {formatScore(record?.scored_marks, record?.max_marks)}
                    {isDisplayableNumber(record?.percentage) ? (
                      <span className="block text-xs text-slate-500">{formatPercent(record.percentage)}</span>
                    ) : null}
                  </td>
                  <td className="max-w-[6rem] truncate px-3 py-2 text-slate-200">{formatText(record?.letter_grade)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  )
}

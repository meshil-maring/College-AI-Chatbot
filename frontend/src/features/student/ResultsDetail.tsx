/**
 * Phase 6.16.2 — Student results DETAIL experience (read-only).
 *
 * Page flow:  Dashboard → Results overview → this page.
 *
 * Layout (per phase spec):
 *
 *   Results
 *   ────────────────────────────
 *   Academic context       <- existing /me/academic-profile contract
 *   Result summary         <- server counts + backend SGPA/CGPA values
 *   Examination results    <- published academic results (own category)
 *   Test scores            <- published per-test scores (own category)
 *
 * Categories are the two that the EXISTING backend contract exposes
 * (`/me/results/summary` and `/me/test-results/summary`). No third category is
 * invented. Every value displayed is a backend field: marks, percentage,
 * grades, SGPA/CGPA and status come straight from the records — the frontend
 * fabricates nothing (no averages, ranks, GPA math, or pass/fail inference).
 *
 * Filter decision (documented in the phase report): the results endpoints
 * accept `academic_year_id` / `semester_id`, but NO student-accessible
 * contract exposes those identifiers (the academic profile returns
 * names/codes only), so no filter control is rendered — frontend-only
 * filtering is forbidden by this phase and inventing identifier sources is
 * out of scope.
 *
 * Independent sections: each category loads, fails, retries, and reports
 * emptiness on its own. A failure in one never destroys the other, and no
 * result error ever destroys the authenticated session (a 401 raises the
 * existing global session-expiry event inside the API client — reused
 * verbatim, no second mechanism).
 */

import {
  getMyAcademicProfile,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../services/studentApi.ts'
import type {
  StudentAcademicResultRecord,
  StudentOwnResults,
  StudentOwnTestResults,
  StudentTestResultRecord,
} from '../../types/student.ts'
import { useStudentResource, type StudentResourceState } from './useStudentResource.ts'
import AcademicContextCard from './AcademicContextCard.tsx'
import { EmptyBlock, ErrorBlock, LoadingBlock, SectionCard, NOT_PROVIDED } from './SectionState.tsx'
import { formatDate, formatLabel, formatNumber, formatPercent, formatScore, formatText } from './studentFormat.ts'

const EMPTY_ACADEMIC_MESSAGE = 'No examination results are available yet.'
const EMPTY_TEST_MESSAGE = 'No test scores are available yet.'
const EMPTY_RESULTS_MESSAGE = 'No results are available for this selection.'
/**
 * Phase 6.16.2 — one user-safe failure message PER category, so the announced
 * error names the section that actually failed and two independent failures are
 * distinguishable in a screen reader's alert queue.
 */
const ACADEMIC_LOAD_ERROR_MESSAGE = 'Unable to load examination results.'
const TEST_LOAD_ERROR_MESSAGE = 'Unable to load test scores.'

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-0.5 truncate text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  )
}


function AcademicResultsTable({ records }: { records: StudentAcademicResultRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[36rem] text-left text-sm">
        <caption className="sr-only">Your published examination results</caption>
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">Result type</th>
            <th scope="col" className="px-3 py-2 font-medium">Credits earned</th>
            <th scope="col" className="px-3 py-2 font-medium">Credits max</th>
            <th scope="col" className="px-3 py-2 font-medium">SGPA</th>
            <th scope="col" className="px-3 py-2 font-medium">CGPA</th>
            <th scope="col" className="px-3 py-2 font-medium">Status</th>
            <th scope="col" className="px-3 py-2 font-medium">Issued</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {records.map((record, index) => (
            <tr key={index}>
              <td className="max-w-[10rem] truncate px-3 py-2 text-slate-200">{formatLabel(record?.result_type)}</td>
              <td className="max-w-[7rem] truncate px-3 py-2 text-slate-200 tabular-nums">{formatNumber(record?.total_credits_earned)}</td>
              <td className="max-w-[7rem] truncate px-3 py-2 text-slate-300 tabular-nums">{formatNumber(record?.total_credits_max)}</td>
              <td className="max-w-[6rem] truncate px-3 py-2 text-slate-200 tabular-nums">{formatNumber(record?.sgpa)}</td>
              <td className="max-w-[6rem] truncate px-3 py-2 text-slate-200 tabular-nums">{formatNumber(record?.cgpa)}</td>
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

function TestScoresTable({ records }: { records: StudentTestResultRecord[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full min-w-[32rem] text-left text-sm">
        <caption className="sr-only">Your published test scores</caption>
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">Test</th>
            <th scope="col" className="px-3 py-2 font-medium">Course</th>
            <th scope="col" className="px-3 py-2 font-medium">Marks</th>
            <th scope="col" className="px-3 py-2 font-medium">Grade</th>
            <th scope="col" className="px-3 py-2 font-medium">Conducted</th>
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
                {formatScore(record?.scored_marks, record?.max_marks)}
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
function courseLabel(courseName: unknown, courseCode: unknown): string {
  if (typeof courseName === 'string' && courseName.trim() !== '') return courseName
  if (typeof courseCode === 'string' && courseCode.trim() !== '') return courseCode
  return NOT_PROVIDED
}

function AcademicResultsSection({ results }: { results: StudentResourceState<StudentOwnResults> }) {
  if (results.status === 'loading' || results.status === 'idle') {
    return <LoadingBlock label="Loading examination results…" />
  }
  if (results.status === 'error') {
    return (
      <ErrorBlock
        message={results.error ?? ACADEMIC_LOAD_ERROR_MESSAGE}
        onRetry={results.reload}
      />
    )
  }
  const rawRecords = results.data?.records
  const records = Array.isArray(rawRecords) ? rawRecords : []
  if (results.data?.summary.records_available !== true || records.length === 0) {
    return <EmptyBlock message={EMPTY_ACADEMIC_MESSAGE} />
  }
  return <AcademicResultsTable records={records} />
}

function TestScoresSection({ testResults }: { testResults: StudentResourceState<StudentOwnTestResults> }) {
  if (testResults.status === 'loading' || testResults.status === 'idle') {
    return <LoadingBlock label="Loading test scores…" />
  }
  if (testResults.status === 'error') {
    return (
      <ErrorBlock
        message={testResults.error ?? TEST_LOAD_ERROR_MESSAGE}
        onRetry={testResults.reload}
      />
    )
  }
  const rawRecords = testResults.data?.records
  const records = Array.isArray(rawRecords) ? rawRecords : []
  if (testResults.data?.summary.records_available !== true || records.length === 0) {
    return <EmptyBlock message={EMPTY_TEST_MESSAGE} />
  }
  return <TestScoresTable records={records} />
}

function ResultsSummaryFigures({
  results,
  testResults,
}: {
  results: StudentResourceState<StudentOwnResults>
  testResults: StudentResourceState<StudentOwnTestResults>
}) {
  const academicRecords =
    results.status === 'loaded' && Array.isArray(results.data?.records) ? results.data.records : []
  // Latest SGPA/CGPA are backend fields on the newest record — displayed
  // verbatim, never recomputed.
  const latestAcademic = academicRecords.length > 0 ? (academicRecords[0] ?? null) : null
  const bothLoading = (results.status === 'loading' || results.status === 'idle') &&
    (testResults.status === 'loading' || testResults.status === 'idle')
  if (bothLoading) return <LoadingBlock label="Loading your results…" />
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Figure
        label="Examination results"
        value={results.status === 'loaded' ? availableCount(results.data?.summary) : NOT_PROVIDED}
      />
      <Figure
        label="Test scores"
        value={testResults.status === 'loaded' ? availableCount(testResults.data?.summary) : NOT_PROVIDED}
      />
      <Figure label="Latest SGPA" value={formatNumber(latestAcademic?.sgpa)} />
      <Figure label="Latest CGPA" value={formatNumber(latestAcademic?.cgpa)} />
    </dl>
  )
}

export function ResultsDetailPage() {
  const profile = useStudentResource(getMyAcademicProfile, 'Unable to load your academic context.')
  const results = useStudentResource(getMyResultsSummary, ACADEMIC_LOAD_ERROR_MESSAGE)
  const testResults = useStudentResource(getMyTestResultsSummary, TEST_LOAD_ERROR_MESSAGE)

  const bothUnavailable =
    results.status === 'loaded' &&
    testResults.status === 'loaded' &&
    results.data?.summary.records_available !== true &&
    testResults.data?.summary.records_available !== true

  return (
    <div className="min-w-0 space-y-4 overflow-x-clip">
      <SectionCard title="Academic context" headingId="student-results-context">
        <AcademicContextCard profile={profile} />
      </SectionCard>

      <SectionCard title="Results summary" headingId="student-results-summary">
        <ResultsSummaryFigures results={results} testResults={testResults} />
        {bothUnavailable ? (
          <div className="mt-3">
            <EmptyBlock message={EMPTY_RESULTS_MESSAGE} />
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Examination results" headingId="student-results-academic">
        <AcademicResultsSection results={results} />
      </SectionCard>

      <SectionCard title="Test scores" headingId="student-results-tests">
        <TestScoresSection testResults={testResults} />
      </SectionCard>
    </div>
  )
}

/** Backend count only when the server says records exist; never a bare "0". */
function availableCount(summary: { records_available: boolean; total_results: number } | null | undefined): string {
  if (summary?.records_available === true) return String(summary.total_results)
  return NOT_PROVIDED
}
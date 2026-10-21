import { getMyAcademicProfile, getMyResultsSummary, getMyTestResultsSummary } from '../../../services/students/studentApi.ts'
import type { StudentOwnResults, StudentOwnTestResults } from '../../../types/student.ts'
import AcademicContextCard from '../shared/AcademicContextCard.tsx'
import { AcademicResultsTable, Figure, TestScoresTable } from './ResultsTables.tsx'
import { EmptyBlock, ErrorBlock, LoadingBlock, NOT_PROVIDED, SectionCard } from '../shared/SectionState.tsx'
import { formatNumber } from '../shared/studentFormat.ts'
import { useStudentResource, type StudentResourceState } from '../shared/useStudentResource.ts'
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

function AcademicResultsSection({ results }: { results: StudentResourceState<StudentOwnResults> }) {
  if (results.status === 'loading' || results.status === 'idle') {
    return <LoadingBlock label="Loading examination results…" />
  }
  if (results.status === 'error') {
    return <ErrorBlock message={results.error ?? ACADEMIC_LOAD_ERROR_MESSAGE} onRetry={results.reload} />
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
    return <ErrorBlock message={testResults.error ?? TEST_LOAD_ERROR_MESSAGE} onRetry={testResults.reload} />
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
  const bothLoading =
    (results.status === 'loading' || results.status === 'idle') &&
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
  const profile = useStudentResource(
    getMyAcademicProfile,
    'Unable to load your academic context.',
    '',
    'academic-profile',
  )
  const results = useStudentResource(getMyResultsSummary, ACADEMIC_LOAD_ERROR_MESSAGE, '', 'results-detail')
  const testResults = useStudentResource(getMyTestResultsSummary, TEST_LOAD_ERROR_MESSAGE, '', 'test-results-detail')

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

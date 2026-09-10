/**
 * Phase Admin-4 — Student My Academics panel.
 *
 * Shows the authenticated student's own profile, results, test results,
 * and attendance. All data is resolved server-side from the JWT.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProvider.tsx'
import {
  getMyAttendance,
  getMyProfile,
  getMyResults,
  getMyTestResults,
} from '../../services/adminApi.ts'
import type {
  AttendanceRecord,
  StudentProfile,
  StudentResult,
  TestResult,
} from '../../types/admin.ts'

type AcademicsTab = 'profile' | 'results' | 'test-results' | 'attendance'

const TABS: { key: AcademicsTab; label: string }[] = [
  { key: 'profile', label: 'Profile' },
  { key: 'results', label: 'Results' },
  { key: 'test-results', label: 'Test Results' },
  { key: 'attendance', label: 'Attendance' },
]

export default function AcademicsPanel() {
  const { accessToken } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<AcademicsTab>('profile')
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [results, setResults] = useState<StudentResult[]>([])
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    if (accessToken === null) return
    try { setProfile(await getMyProfile(accessToken)) } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load profile.') }
  }, [accessToken])

  const loadResults = useCallback(async () => {
    if (accessToken === null) return
    try { setResults(await getMyResults(accessToken)) } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load results.') }
  }, [accessToken])

  const loadTestResults = useCallback(async () => {
    if (accessToken === null) return
    try { setTestResults(await getMyTestResults(accessToken)) } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load test results.') }
  }, [accessToken])

  const loadAttendance = useCallback(async () => {
    if (accessToken === null) return
    try { setAttendance(await getMyAttendance(accessToken)) } catch (err) { setError(err instanceof Error ? err.message : 'Failed to load attendance.') }
  }, [accessToken])

  useEffect(() => {
    if (!isOpen || accessToken === null) return
    setIsLoading(true)
    setError(null)
    void Promise.all([loadProfile(), loadResults(), loadTestResults(), loadAttendance()]).finally(() => setIsLoading(false))
  }, [isOpen, accessToken, loadProfile, loadResults, loadTestResults, loadAttendance])

  if (!isOpen) {
    return (
      <div className="border-t border-slate-700 bg-slate-800/60 px-4 py-3">
        <button type="button" onClick={() => setIsOpen(true)} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400">My Academics</button>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-3xl max-h-[80vh] flex flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-700 px-6 py-4">
          <h2 className="text-lg font-bold text-white">My Academics</h2>
          <button type="button" onClick={() => setIsOpen(false)} className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400">Close</button>
        </div>
        <div className="border-b border-slate-700 px-6">
          <nav className="flex gap-1" aria-label="Academics sections">
            {TABS.map((tab) => (
              <button key={tab.key} type="button" onClick={() => setActiveTab(tab.key)} aria-current={activeTab === tab.key ? 'page' : undefined} className={`px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-400 ${activeTab === tab.key ? 'border-b-2 border-emerald-400 text-white' : 'text-slate-400 hover:text-white'}`}>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {error !== null && <div role="alert" className="mb-4 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</div>}
          {isLoading ? <p className="text-sm text-slate-400">Loading…</p> : <TabContent profile={profile} results={results} testResults={testResults} attendance={attendance} activeTab={activeTab} />}
        </div>
      </div>
    </div>
  )
}

function TabContent({ profile, results, testResults, attendance, activeTab }: {
  profile: StudentProfile | null
  results: StudentResult[]
  testResults: TestResult[]
  attendance: AttendanceRecord[]
  activeTab: AcademicsTab
}) {
  if (activeTab === 'profile' && profile) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <Info label="Student Number" value={profile.student_number} />
        <Info label="Status" value={profile.status} />
        <Info label="Enrollment Date" value={profile.enrollment_date ?? '—'} />
        <Info label="Expected Graduation" value={profile.expected_graduation_date ?? '—'} />
      </div>
    )
  }
  if (activeTab === 'results') {
    return results.length === 0 ? <p className="text-sm text-slate-400">No results available.</p> : (
      <Table cols={['Type', 'SGPA', 'CGPA', 'Status']}>
        {results.map((r) => (
          <tr key={r.student_result_id}><Td>{r.result_type}</Td><Td>{r.sgpa ?? '—'}</Td><Td>{r.cgpa ?? '—'}</Td><Td muted>{r.status}</Td></tr>
        ))}
      </Table>
    )
  }
  if (activeTab === 'test-results') {
    return testResults.length === 0 ? <p className="text-sm text-slate-400">No test results available.</p> : (
      <Table cols={['Test', 'Score', 'Percentage', 'Grade']}>
        {testResults.map((r) => (
          <tr key={r.test_result_id}><Td>{r.test_name}</Td><Td>{r.scored_marks ?? '—'}/{r.max_marks ?? '—'}</Td><Td>{r.percentage != null ? `${r.percentage}%` : '—'}</Td><Td>{r.letter_grade ?? '—'}</Td></tr>
        ))}
      </Table>
    )
  }
  if (activeTab === 'attendance') {
    return attendance.length === 0 ? <p className="text-sm text-slate-400">No attendance records available.</p> : (
      <Table cols={['Date', 'Status', 'Notes']}>
        {attendance.map((r) => (
          <tr key={r.student_attendance_id}><Td>{r.date}</Td><Td>{r.status}</Td><Td muted>{r.notes ?? '—'}</Td></tr>
        ))}
      </Table>
    )
  }
  return null
}

function Table({ cols, children }: { cols: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-800 text-xs text-slate-400">
          <tr>{cols.map((c) => <th key={c} className="px-4 py-2">{c}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-700">{children}</tbody>
      </table>
    </div>
  )
}

function Td({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return <td className={`px-4 py-2 ${muted ? 'text-slate-400' : 'text-slate-300'}`}>{children}</td>
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-1 text-sm font-medium text-white">{value}</div>
    </div>
  )
}

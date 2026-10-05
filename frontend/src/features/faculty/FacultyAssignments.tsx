import { useEffect, useState } from 'react'
import { getMyFacultyAssignments } from '../../services/adminApi.ts'

type Assignments = Awaited<ReturnType<typeof getMyFacultyAssignments>>

export default function FacultyAssignments({ accessToken }: { accessToken: string }) {
  const [assignments, setAssignments] = useState<Assignments>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    getMyFacultyAssignments(accessToken)
      .then((rows) => { if (current) setAssignments(rows) })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : 'Could not load section assignments.')
      })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [accessToken])

  if (loading) return <p role="status">Loading assigned sections…</p>
  if (error) return <p role="alert" className="rounded-lg border border-red-700 p-3 text-sm text-red-200">{error}</p>
  if (assignments.length === 0) return <p className="text-slate-300">No active section assignments are available.</p>

  return (
    <section aria-label="My active section assignments" className="space-y-3">
      {assignments.map((assignment) => (
        <article key={assignment.assignment_id} className="rounded-xl border border-slate-700 bg-slate-800 p-4">
          <h2 className="font-semibold text-white">{assignment.section.course.code} · {assignment.section.code}</h2>
          <p className="mt-1 text-sm text-slate-300">{assignment.section.course.name} — {assignment.section.name}</p>
        </article>
      ))}
    </section>
  )
}

import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { getMyFacultyAssignments } from '../../services/adminApi.ts'

type Assignments = Awaited<ReturnType<typeof getMyFacultyAssignments>>

export default function FacultyAssignments({ accessToken }: { accessToken: string }) {
  const query = useApiQuery<Assignments>(
    ['faculty', 'assignments', accessToken],
    () => getMyFacultyAssignments(accessToken),
  )
  const assignments = query.data ?? []
  const loading = query.isPending
  const error = query.isError
    ? (query.error instanceof Error ? query.error.message : 'Could not load section assignments.')
    : null

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

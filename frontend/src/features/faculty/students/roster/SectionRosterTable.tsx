import { attendance, STATUS_LABELS, STATUS_TONE } from './rosterUi.tsx'
import type { SectionStudentsModel } from './useSectionStudents.ts'

export function SectionRosterTable({ model }: { model: SectionStudentsModel }) {
  const { assignment, setStudentId, result, selectedStudent } = model
  if (result === undefined) return null
  return (
    <table className="students-table directory">
      <caption className="sr-only">Students in {assignment.section.name}</caption>
      <thead>
        <tr>
          {['Student', 'Register number', 'University roll number', 'Registration', 'Attendance', 'Details'].map(
            (label) => (
              <th scope="col" key={label}>
                {label}
              </th>
            ),
          )}
        </tr>
      </thead>
      <tbody>
        {result.items.map((row) => (
          <tr key={row.roster_id} className={STATUS_TONE[row.roster_status]}>
            <td className="student-name">
              <p className="font-medium text-white">{row.student_name}</p>
              <p className="mt-1 text-xs text-slate-400">{row.email ?? 'Email not recorded'}</p>
            </td>
            <td>{row.register_number}</td>
            <td>{row.university_roll_number ?? '—'}</td>
            <td>
              <span className={`students-status ${STATUS_TONE[row.roster_status]}`}>
                {STATUS_LABELS[row.roster_status]}
              </span>
            </td>
            <td>{attendance(row.attendance_percentage)}</td>
            <td>
              <button
                type="button"
                className="students-button"
                aria-label={`View ${row.student_name}`}
                aria-expanded={selectedStudent?.roster_id === row.roster_id}
                onClick={() => setStudentId(row.roster_id)}
              >
                View student
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

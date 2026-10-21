import { useState } from 'react'
import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { useStudentWorkspaceApi } from '../../../students/StudentWorkspaceContext.tsx'
import type { ClassRegistrationFilters, ClassStudentRegistration } from '../../../../services/students/studentRegistrationApi.ts'

export default function ClassRegistrationDirectory({ token, sectionId, waitingApproval = false, registration, filters }: { token: string; sectionId: string; waitingApproval?: boolean; registration?: ClassStudentRegistration['roster_status']; filters?: ClassRegistrationFilters }) {
  const api = useStudentWorkspaceApi()
  const [page, setPage] = useState(0)
  const status = waitingApproval ? 'PENDING_APPROVAL' : registration
  const query = useApiQuery([api.namespace, 'class-registrations', token, sectionId, page, status, filters], () => api.getRegistrations(token, sectionId, page * 25, 25, status, filters))
  if (query.isError) return <div className="students-alert error" role="alert"><span>{query.error instanceof Error ? query.error.message : 'Class registrations could not be loaded.'}</span><button type="button" className="students-button" onClick={() => void query.refetch()}>Retry class registrations</button></div>
  if (!query.data?.items.length) return null
  const rows = waitingApproval ? query.data.items.filter((row) => row.roster_status === 'PENDING_APPROVAL') : query.data.items
  if (!rows.length) return null
  return <section className="students-directory" aria-label="Class registrations">
    <div className="students-toolbar"><div className="students-toolbar-heading"><h2>{waitingApproval ? 'Class registrations waiting for approval' : 'Class registrations'}</h2><p>Students registered by course, branch, section, and admission batch. Subjects can be assigned later.</p></div></div>
    <div className="students-table-scroll"><table className="students-table directory">
      <caption className="sr-only">Students registered without subject assignments</caption>
      <thead><tr><th>Student</th><th>Register number</th><th>Section</th><th>Batch</th><th>Registration status</th><th>Subjects</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.registration_id}><td className="student-name">{row.student_name}</td><td>{row.register_number}</td><td>{row.section_code}</td><td>{row.batch_start_year}–{row.batch_end_year}</td><td>{row.identity_conflict ? 'Identity review required' : row.roster_status === 'PENDING_APPROVAL' ? 'Pending approval' : row.roster_status === 'ACTIVE' ? 'Active' : row.roster_status === 'INACTIVE' ? 'Inactive' : 'Not signed up'}</td><td>Assign later</td></tr>)}</tbody>
    </table></div>
    <div className="students-pagination"><p>{query.data.total} class registrations</p><div><button type="button" className="students-button" disabled={page === 0 || query.isFetching} onClick={() => setPage(page - 1)}>Previous registrations</button><span>Page {page + 1}</span><button type="button" className="students-button" disabled={(page + 1) * 25 >= query.data.total || query.isFetching} onClick={() => setPage(page + 1)}>Next registrations</button></div></div>
  </section>
}

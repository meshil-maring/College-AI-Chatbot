import { useState } from 'react'
import { assignStudentSemester } from '../../../../services/academics/semesterRegistration.ts'
import { useAcademicStructure, type StructureContext } from '../structure/useAcademicStructure.ts'
import StructureState from '../structure/StructureState.tsx'
import { useRegistrationAdmin } from './useRegistrationAdmin.ts'
import './registration.css'

export default function StudentEnrollmentPage({ context, onBack }: { context: StructureContext; onBack: () => void }) {
  const structure = useAcademicStructure(context)
  const state = useRegistrationAdmin(context)
  const [studentId, setStudentId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const sections = structure.structure?.records.academic_sections ?? []
  function sectionLabel(id: string) {
    const section = sections.find((item) => item.academic_section_id === id)
    const batch = structure.structure?.records.admission_cohorts?.find(
      (item) => item.admission_cohort_id === section?.admission_cohort_id,
    )
    const stage = structure.structure?.records.program_semesters?.find(
      (item) => item.program_semester_id === section?.program_semester_id,
    )
    const term = structure.catalogue?.records.semesters?.find((item) => item.semester_id === section?.semester_id)
    return `${batch?.name ?? ''} · ${stage?.name ?? ''} · ${section?.name ?? 'Section unavailable'} · ${term?.name ?? ''}`
  }
  async function save() {
    if (await state.save(() => assignStudentSemester(context.accessToken, studentId, sectionId))) setStudentId('')
  }
  return (
    <section className="academic-workspace semester-registration" aria-label="Student semester enrollment">
      <button type="button" className="academic-back-button" onClick={onBack}>
        Back to Sections
      </button>
      <h1>Student Enrollment</h1>
      <p>
        Assign an approved student to a batch section and teaching term. The student can then choose their subject
        option in Semester Registration.
      </p>
      <StructureState state={structure} />
      {state.query.isPending && <p role="status">Loading student enrollment…</p>}
      {state.error instanceof Error && (
        <div role="alert">
          <p>{state.error.message}</p>
          <button type="button" className="academic-secondary-button" onClick={() => void state.query.refetch()}>
            Retry
          </button>
        </div>
      )}
      {state.notice && <p role="status">{state.notice}</p>}
      {state.data && !state.data.can_assign && (
        <p role="status">Assigning students requires Courses manage, Students read, and Students update permissions.</p>
      )}
      {state.data?.can_assign && (
        <form
          className="registration-panel"
          onSubmit={(event) => {
            event.preventDefault()
            void save()
          }}
        >
          <fieldset disabled={state.busy || structure.busy}>
            <div className="registration-grid">
              <label>
                Student
                <select required value={studentId} onChange={(event) => setStudentId(event.target.value)}>
                  <option value="">Select an approved student</option>
                  {state.data.students.map((student) => (
                    <option key={student.student_id} value={student.student_id}>
                      {student.student_number}
                      {student.email ? ` · ${student.email}` : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Academic Section
                <select required value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
                  <option value="">Select a section</option>
                  {sections
                    .filter((section) => section.is_active)
                    .map((section) => (
                      <option key={section.academic_section_id} value={section.academic_section_id}>
                        {sectionLabel(section.academic_section_id)}
                      </option>
                    ))}
                </select>
              </label>
            </div>
            <button type="submit" className="academic-primary-button" disabled={!studentId || !sectionId}>
              {state.saving ? 'Assigning…' : 'Assign student'}
            </button>
          </fieldset>
        </form>
      )}
      <div className="registration-panel">
        <h2>Semester assignments</h2>
        {state.data && !state.data.assignments.length && <p>No semester assignments yet.</p>}
        {state.data?.assignments.map((assignment) => (
          <article key={assignment.semester_registration_id}>
            <h3>
              {state.data?.students.find((student) => student.student_id === assignment.student_id)?.student_number ??
                'Student'}
            </h3>
            <p>{sectionLabel(assignment.academic_section_id)}</p>
            <p>Status: {assignment.status === 'registered' ? 'Registered' : 'Awaiting subject selection'}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

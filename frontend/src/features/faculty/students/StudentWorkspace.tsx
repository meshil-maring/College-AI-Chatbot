import type { UseQueryResult } from '@tanstack/react-query'
import { Users } from 'lucide-react'
import { useState } from 'react'
import { type FacultyAttendanceAssignment } from '../../../services/faculty/facultyAttendanceApi.ts'
import StudentRosterFilters from '../../students/StudentRosterFilters.tsx'
import SubjectAssignment from '../../students/subject-assignment/SubjectAssignment.tsx'
import type { StudentRegistrationMethod } from '../../students/studentsNavigation.ts'
import { StudentsPageHeader } from '../../students/StudentsUI.tsx'
import { useStudentWorkspaceApi } from '../../students/StudentWorkspaceContext.tsx'
import { type FacultyStudentPage } from '../workspace/facultyRoutes.ts'
import FacultyStudentRecordHistory from './FacultyStudentRecordHistory.tsx'
import { LoadError, panel, STUDENT_PAGE_LABELS } from './roster/rosterUi.tsx'
import { SectionStudents } from './roster/SectionStudents.tsx'
export function StudentWorkspace({
  accessToken,
  page,
  sectionId,
  assignmentsQuery,
  assignments,
  selected,
  onNavigate,
  registrationMethod,
  onRegistrationMethod,
  initialSearch,
  packageAccess,
}: {
  accessToken: string
  page: FacultyStudentPage
  sectionId: string
  assignmentsQuery: Pick<
    UseQueryResult<FacultyAttendanceAssignment[], unknown>,
    'isError' | 'isPending' | 'isFetching' | 'error' | 'refetch'
  >
  assignments: FacultyAttendanceAssignment[]
  selected?: FacultyAttendanceAssignment
  onNavigate: (page: FacultyStudentPage, sectionId: string, replace?: boolean) => void
  registrationMethod?: StudentRegistrationMethod
  onRegistrationMethod?: (method: StudentRegistrationMethod) => void
  initialSearch?: string
  packageAccess?: boolean
}) {
  const api = useStudentWorkspaceApi()
  const registrationOpen = page === 'register'
  const [batchSelection, setBatchSelection] = useState({ programId: '', batchId: '' })
  const programId = selected?.section.program_id ?? selected?.section.program?.program_id ?? ''
  const batchId = batchSelection.programId === programId ? batchSelection.batchId : ''
  const changeBatch = (id: string) => setBatchSelection({ programId, batchId: id })

  return (
    <div className="students-content students-scope">
      <StudentsPageHeader
        page={STUDENT_PAGE_LABELS[page]}
        title={registrationOpen ? undefined : 'Students'}
        description={
          api.namespace === 'admin'
            ? "Browse student rosters across your institution. Registration status and attendance reflect your institution's records."
            : "Browse student rosters in your authorized sections. Registration status and attendance reflect your institution's records."
        }
      />
      {assignmentsQuery.isError ? (
        <LoadError
          error={assignmentsQuery.error}
          onRetry={() => {
            void assignmentsQuery.refetch()
          }}
        />
      ) : assignmentsQuery.isPending ? (
        <p role="status" className={`${panel} text-sm text-slate-400`}>
          Loading your sections…
        </p>
      ) : registrationOpen && !selected?.can_manage && (api.namespace !== 'admin' || assignments.length > 0) ? (
        <section className={`${panel} space-y-4`}>
          <h1 className="text-2xl font-bold text-white">Registration unavailable</h1>
          <p role="alert" className="text-sm text-slate-400">
            You do not have permission to register students in this section. Choose a section you can manage from
            Students.
          </p>
        </section>
      ) : !selected ? (
        <section className="students-empty">
          <Users aria-hidden="true" className="mx-auto mb-4 h-10 w-10 text-[#ffc72c]" />
          <h2 className="text-lg font-semibold text-white">
            {sectionId ? 'Section unavailable' : 'No student rosters available'}
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            {api.namespace === 'admin'
              ? 'Create active sections in Academic Setup before managing student rosters.'
              : 'Student rosters appear when your institution grants you access to an active section.'}
          </p>
          <button
            type="button"
            className="students-button"
            disabled={assignmentsQuery.isFetching}
            onClick={() => void assignmentsQuery.refetch()}
          >
            Refresh sections
          </button>
        </section>
      ) : (
        <>
          {!registrationOpen ? (
            <StudentRosterFilters
              key={`filters:${selected.section_id}`}
              token={accessToken}
              assignments={assignments}
              selected={selected}
              batchId={batchId}
              onBatch={changeBatch}
              onSection={(id) => onNavigate(page, id, true)}
              onRefresh={() => {
                void assignmentsQuery.refetch()
              }}
              refreshing={assignmentsQuery.isFetching}
              showBatch={page !== 'history'}
            />
          ) : null}
          {page === 'subject-assignment' ? (
            <SubjectAssignment
              key={`${selected.section_id}:${batchId}`}
              token={accessToken}
              assignment={selected}
              batchId={batchId}
              packageAccess={packageAccess}
            />
          ) : page === 'history' ? (
            <FacultyStudentRecordHistory key={selected.section_id} token={accessToken} assignment={selected} />
          ) : (
            <SectionStudents
              key={`${selected.section_id}:${page === 'waiting-approval' ? 'waiting' : 'roster'}:${initialSearch ?? ''}`}
              token={accessToken}
              assignment={selected}
              assignments={assignments}
              batchId={batchId}
              onClearBatch={() => changeBatch('')}
              onSectionChange={(nextSectionId) => onNavigate('register', nextSectionId, true)}
              registrationOpen={registrationOpen}
              waitingApproval={page === 'waiting-approval'}
              onRegister={() => onNavigate('register', selected.section_id)}
              onBack={() => onNavigate('roster', selected.section_id, true)}
              registrationMethod={registrationMethod}
              onRegistrationMethod={onRegistrationMethod}
              initialSearch={initialSearch}
            />
          )}
        </>
      )}
    </div>
  )
}

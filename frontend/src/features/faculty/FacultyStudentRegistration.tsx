import { useEffect, useRef, useState } from 'react'
import { useApiMutation, useApiQuery } from '../../hooks/useApiQuery.ts'
import { queryClient } from '../../lib/queryClient.ts'
import { AdminApiError } from '../../services/adminApi.ts'
import type { FacultyAttendanceAssignment } from '../../services/facultyAttendanceApi.ts'
import type { ClassStudentRegistration } from '../../services/studentRegistrationApi.ts'
import StudentImport, { type StudentImportOutcome } from '../admin/students/StudentImport.tsx'
import type { ReviewStudent } from '../admin/students/studentImport.ts'
import { loadRegistrationRoster, readRegistrationFile, reviewStudentRegistrations } from './facultyStudentImport.ts'
import RegistrationAcademicSelection, { registrationClasses } from './RegistrationAcademicSelection.tsx'
import { StudentRegistrationMethods, StudentsPageTitle } from '../students/StudentsUI.tsx'
import { useStudentWorkspaceApi } from '../students/StudentWorkspaceContext.tsx'
import type { StudentRegistrationMethod } from '../students/studentsNavigation.ts'

const input = 'mt-1 w-full rounded-lg border border-[#304862] bg-[#091725] px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#ffc72c]'
const button = 'rounded-lg border border-[#304862] px-3 py-2 text-sm text-slate-200 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
const primaryButton = 'rounded-lg bg-[#ffc72c] px-3 py-2 text-sm font-semibold text-[#101820] hover:bg-[#ffd65d] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'

export default function FacultyStudentRegistration({ token, assignment, assignments, onSectionChange, onRegistered, onCancel, method, onMethodChange }: {
  token: string
  assignment: FacultyAttendanceAssignment
  assignments: FacultyAttendanceAssignment[]
  onSectionChange: (sectionId: string) => void
  onRegistered: (student: ClassStudentRegistration) => void
  onCancel: () => void
  method?: StudentRegistrationMethod
  onMethodChange?: (method: StudentRegistrationMethod) => void
}) {
  const api = useStudentWorkspaceApi()
  const [fields, setFields] = useState({ student_name: '', register_number: '', university_roll_number: '', email: '' })
  const [validationError, setValidationError] = useState('')
  const [localMode, setLocalMode] = useState<StudentRegistrationMethod>('individual')
  const mode = method ?? localMode
  const setMode = (next: StudentRegistrationMethod) => { setLocalMode(next); onMethodChange?.(next) }
  const [importBusy, setImportBusy] = useState(false)
  const [batch, setBatch] = useState('')
  const hasClass = registrationClasses(assignments).some((item) => item.ids.includes(assignment.section_id))
  const batchesQuery = useApiQuery(
    [api.namespace, 'registration-batches', token, assignment.section_id],
    () => api.getBatches(token, assignment.section_id), hasClass,
  )
  const batches = batchesQuery.isError ? [] : batchesQuery.data ?? []
  const selectedBatch = batches.find((item) => item.batch_id === batch && item.is_active && item.program_id === (assignment.section.program_id ?? assignment.section.program?.program_id))
  const cohort = selectedBatch && batchesQuery.isSuccess && !batchesQuery.isFetching ? { batch_id: selectedBatch.batch_id } : null
  const batchLabel = selectedBatch ? `${selectedBatch.start_year}–${selectedBatch.end_year}` : ''
  const existingQuery = useApiQuery(
    [api.namespace, 'students', token, assignment.section_id, 'registration-roster'],
    () => loadRegistrationRoster(token, assignment.section_id, api.getRegistrations),
    mode === 'bulk',
  )
  const active = useRef(false)
  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [])
  const registration = useApiMutation({
    mutationFn: (data: typeof fields) => {
      if (!cohort || !hasClass) throw new Error('Select a course, branch, section, and an active batch from Academic Setup.')
      return api.createRegistration(token, assignment.section_id, {
        student_name: data.student_name,
        register_number: data.register_number,
        ...(data.university_roll_number ? { university_roll_number: data.university_roll_number } : {}),
        ...(data.email ? { email: data.email } : {}),
        ...cohort,
      })
    },
    onSuccess: (student) => {
      void queryClient.invalidateQueries({ queryKey: [api.namespace, 'class-registrations', token] })
      void queryClient.invalidateQueries({ queryKey: [api.namespace, 'students', token, assignment.section_id] })
      void queryClient.invalidateQueries({ queryKey: [api.namespace, 'attendance', token] })
      if (active.current) onRegistered(student)
    },
  })

  async function registerRows(rows: ReviewStudent[], onProgress: (completed: number) => void): Promise<StudentImportOutcome[]> {
    if (!cohort || !hasClass) throw new Error('Select a course, branch, section, and an active batch before importing.')
    const outcomes: StudentImportOutcome[] = []
    let stopReason = ''
    for (const row of rows) {
      if (!active.current) break
      if (stopReason) {
        outcomes.push({ row: row.row, name: row.name, status: 'failed', message: `Not attempted: ${stopReason}` })
        onProgress(outcomes.length)
        continue
      }
      try {
        await api.createRegistration(token, assignment.section_id, {
          student_name: row.name, register_number: row.registerNumber,
          ...(row.rollNumber ? { university_roll_number: row.rollNumber } : {}),
          ...(row.email ? { email: row.email } : {}),
          ...cohort,
        })
        outcomes.push({ row: row.row, name: row.name, status: 'imported', message: `Registered in Section ${assignment.section.code}, batch ${batchLabel}. Subjects can be assigned later.` })
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Student could not be registered.'
        outcomes.push({ row: row.row, name: row.name, status: 'failed', message })
        if (error instanceof AdminApiError && ([401, 403].includes(error.status) || error.code === 'BATCH_UNAVAILABLE')) stopReason = message
      }
      onProgress(outcomes.length)
    }
    void queryClient.invalidateQueries({ queryKey: [api.namespace, 'students', token] })
    void queryClient.invalidateQueries({ queryKey: [api.namespace, 'class-registrations', token] })
    void queryClient.invalidateQueries({ queryKey: [api.namespace, 'attendance', token] })
    return outcomes
  }

  const busy = registration.isPending || importBusy

  return <div className={`mx-auto space-y-5 ${mode === 'individual' ? 'max-w-3xl' : 'w-full'}`}>
    <StudentsPageTitle title={mode === 'bulk' ? 'Bulk Student Import' : 'Register new student'} description={mode === 'bulk' ? 'Upload a spreadsheet, review student records, and register the selected students.' : 'Register a student in a course, branch, section, and admission batch.'} />
    <StudentRegistrationMethods mode={mode} onChange={setMode} disabled={busy} placement={<>
    <RegistrationAcademicSelection assignments={assignments} sectionId={assignment.section_id} batch={batch} batches={batches} batchesLoading={batchesQuery.isFetching} onBatch={setBatch} onSectionChange={onSectionChange} disabled={busy} />
    <div className="flex items-center gap-3 text-sm">
      <button type="button" className={button} disabled={busy || batchesQuery.isFetching || !hasClass} onClick={() => void batchesQuery.refetch()}>Refresh batches</button>
      {batchesQuery.isError && <p role="alert" className="text-red-300">{batchesQuery.error instanceof Error ? batchesQuery.error.message : 'Batches could not be loaded.'}</p>}
    </div>
    </>}>
    {mode === 'bulk' ? <>
      {existingQuery.isError && <div role="alert" className="students-alert error"><span>{existingQuery.error instanceof Error ? existingQuery.error.message : 'Section roster could not be loaded.'}</span><button type="button" className="students-button" onClick={() => void existingQuery.refetch()}>Retry roster checks</button></div>}
      {!cohort && <p className="students-alert" role="status">Select an active admission batch before confirming the import.</p>}
      <StudentImport students={[]} directoryReady={existingQuery.isSuccess && !existingQuery.isFetching && !!cohort && hasClass} onBack={onCancel} registration={{
        readFile: readRegistrationFile,
        reviewRows: (rows) => reviewStudentRegistrations(rows, existingQuery.data ?? []),
        importRows: registerRows,
        onBusyChange: setImportBusy,
      }} />
    </> : <form aria-label="Register student" className="space-y-4 rounded-lg border border-[#304862] bg-[#091725] p-4" onSubmit={(event) => {
      event.preventDefault()
      if (registration.isPending) return
      const data = { student_name: fields.student_name.trim(), register_number: fields.register_number.trim(), university_roll_number: fields.university_roll_number.trim(), email: fields.email.trim() }
      if (!data.student_name || !data.register_number) {
        setValidationError('Enter a student name and register number.')
        return
      }
      setValidationError('')
      if (!cohort || !hasClass) {
        setValidationError('Select a course, branch, section, and an active batch from Academic Setup.')
        return
      }
      registration.mutate(data)
    }}>
      <div><h2 className="font-semibold text-white">Student information</h2>
        <p className="mt-1 text-sm text-slate-400">Register a student in Section {assignment.section.code}. Subjects can be assigned later. Existing accounts are matched by academic identifiers; new students must complete account signup and approval to sign in.</p>
      </div>
      <fieldset disabled={registration.isPending} className="grid gap-4 sm:grid-cols-2">
        <legend className="sr-only">New student information</legend>
        <label className="text-sm text-slate-300">Student name (required)<input autoFocus className={input} required maxLength={256} autoComplete="name" value={fields.student_name} onChange={(event) => setFields((previous) => ({ ...previous, student_name: event.target.value }))} /></label>
        <label className="text-sm text-slate-300">Register number (required)<input className={input} required maxLength={128} value={fields.register_number} onChange={(event) => setFields((previous) => ({ ...previous, register_number: event.target.value }))} /></label>
        <div><label className="text-sm text-slate-300">University roll number<input className={input} maxLength={128} aria-describedby="student-roll-hint" value={fields.university_roll_number} onChange={(event) => setFields((previous) => ({ ...previous, university_roll_number: event.target.value }))} /></label><p id="student-roll-hint" className="mt-1 text-xs text-slate-400">Optional during registration. Add it when available.</p></div>
        <label className="text-sm text-slate-300">Email (optional)<input className={input} type="email" maxLength={128} autoComplete="email" value={fields.email} onChange={(event) => setFields((previous) => ({ ...previous, email: event.target.value }))} /></label>
      </fieldset>
      {validationError || registration.isError ? <p role="alert" className="text-sm text-red-300">{validationError || (registration.error instanceof Error ? registration.error.message : 'Student could not be registered. Please try again.')}</p> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" className={button} disabled={registration.isPending} onClick={onCancel}>Cancel</button>
        <button type="submit" className={primaryButton} disabled={registration.isPending}>{registration.isPending ? 'Registering student…' : 'Register student'}</button>
      </div>
    </form>}
    </StudentRegistrationMethods>
  </div>
}

import { useEffect, useRef, useState } from 'react'
import { useApiMutation } from '../../hooks/useApiQuery.ts'
import { queryClient } from '../../lib/queryClient.ts'
import { addFacultyAttendanceStudent, type FacultyAttendanceAssignment, type FacultyAttendanceRosterRow } from '../../services/facultyAttendanceApi.ts'

const input = 'mt-1 w-full rounded-lg border border-[#304862] bg-[#091725] px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#ffc72c]'
const button = 'rounded-lg border border-[#304862] px-3 py-2 text-sm text-slate-200 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'
const primaryButton = 'rounded-lg bg-[#ffc72c] px-3 py-2 text-sm font-semibold text-[#101820] hover:bg-[#ffd65d] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'

export default function FacultyStudentRegistration({ token, assignment, assignments, onSectionChange, onRegistered, onCancel }: {
  token: string
  assignment: FacultyAttendanceAssignment
  assignments: FacultyAttendanceAssignment[]
  onSectionChange: (sectionId: string) => void
  onRegistered: (student: FacultyAttendanceRosterRow) => void
  onCancel: () => void
}) {
  const [fields, setFields] = useState({ student_name: '', register_number: '', university_roll_number: '', email: '' })
  const [validationError, setValidationError] = useState('')
  const active = useRef(false)
  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [])
  const registration = useApiMutation({
    mutationFn: (data: typeof fields) => addFacultyAttendanceStudent(token, assignment.section_id, {
      student_name: data.student_name,
      register_number: data.register_number,
      ...(data.university_roll_number ? { university_roll_number: data.university_roll_number } : {}),
      ...(data.email ? { email: data.email } : {}),
    }),
    onSuccess: (student) => {
      void queryClient.invalidateQueries({ queryKey: ['faculty', 'students', token, assignment.section_id] })
      void queryClient.invalidateQueries({ queryKey: ['faculty', 'attendance', token] })
      if (active.current) onRegistered(student)
    },
  })

  return <div className="mx-auto max-w-3xl space-y-5">
    <div><h1 className="text-2xl font-bold text-white">Register new student</h1><p className="mt-2 text-sm text-slate-400">Add a student to your selected section roster.</p></div>
    <label className="block rounded-xl border border-[#26394e] bg-[#0d1c2c] p-5 text-sm text-slate-300">Section and subject
      <select className={input} value={assignment.section_id} disabled={registration.isPending} onChange={(event) => onSectionChange(event.target.value)}>
        {assignments.filter((item) => item.can_manage).map(({ section_id, section }) => <option key={section_id} value={section_id}>{section.course.code} · {section.course.name} · {section.name} ({section.code})</option>)}
      </select>
    </label>
    <form aria-label="Register student" className="space-y-4 rounded-lg border border-[#304862] bg-[#091725] p-4" onSubmit={(event) => {
      event.preventDefault()
      if (registration.isPending) return
      const data = { student_name: fields.student_name.trim(), register_number: fields.register_number.trim(), university_roll_number: fields.university_roll_number.trim(), email: fields.email.trim() }
      if (!data.student_name || !data.register_number) {
        setValidationError('Enter a student name and register number.')
        return
      }
      setValidationError('')
      registration.mutate(data)
    }}>
      <div><h2 className="font-semibold text-white">Student information</h2>
        <p className="mt-1 text-sm text-slate-400">Add a student to {assignment.section.name} for {assignment.section.course.name}. Existing student accounts are matched by academic identifiers. New students must complete account signup and approval to sign in.</p>
      </div>
      <fieldset disabled={registration.isPending} className="grid gap-4 sm:grid-cols-2">
        <legend className="sr-only">New student information</legend>
        <label className="text-sm text-slate-300">Student name (required)<input autoFocus className={input} required maxLength={256} autoComplete="name" value={fields.student_name} onChange={(event) => setFields((previous) => ({ ...previous, student_name: event.target.value }))} /></label>
        <label className="text-sm text-slate-300">Register number (required)<input className={input} required maxLength={128} value={fields.register_number} onChange={(event) => setFields((previous) => ({ ...previous, register_number: event.target.value }))} /></label>
        <div><label className="text-sm text-slate-300">University roll number<input className={input} maxLength={128} aria-describedby="student-roll-hint" value={fields.university_roll_number} onChange={(event) => setFields((previous) => ({ ...previous, university_roll_number: event.target.value }))} /></label><p id="student-roll-hint" className="mt-1 text-xs text-slate-400">Required after the first semester.</p></div>
        <label className="text-sm text-slate-300">Email (optional)<input className={input} type="email" maxLength={128} autoComplete="email" value={fields.email} onChange={(event) => setFields((previous) => ({ ...previous, email: event.target.value }))} /></label>
      </fieldset>
      {validationError || registration.isError ? <p role="alert" className="text-sm text-red-300">{validationError || (registration.error instanceof Error ? registration.error.message : 'Student could not be registered. Please try again.')}</p> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" className={button} disabled={registration.isPending} onClick={onCancel}>Cancel</button>
        <button type="submit" className={primaryButton} disabled={registration.isPending}>{registration.isPending ? 'Registering student…' : 'Register student'}</button>
      </div>
    </form>
  </div>
}

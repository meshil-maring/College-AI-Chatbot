import type { FacultyAttendanceAssignment } from '../../services/facultyAttendanceApi.ts'
import type { AcademicBatch } from '../../services/studentRegistrationApi.ts'

const input = 'mt-1 w-full rounded-lg border border-[#304862] bg-[#091725] px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-50'

export function registrationClasses(assignments: FacultyAttendanceAssignment[]) {
  const groups = new Map<string, { id: string; ids: string[]; course: string; branch: string; programId: string; code: string; term: string }>()
  for (const assignment of assignments.filter((item) => item.can_manage)) {
    const section = assignment.section
    const programId = section.program_id ?? section.program?.program_id
    const course = section.program?.degree_type?.trim()
    if (!programId || !course || !section.program?.name) continue
    const key = JSON.stringify([programId, assignment.academic_year_id, assignment.semester_id, section.code])
    const existing = groups.get(key)
    if (existing) existing.ids.push(assignment.section_id)
    else groups.set(key, { id: assignment.section_id, ids: [assignment.section_id], course, branch: section.program.name, programId, code: section.code,
      term: [section.semester?.name, section.academic_year?.name].filter(Boolean).join(' · ') })
  }
  return [...groups.values()]
}

export default function RegistrationAcademicSelection({ assignments, sectionId, batch, batches, batchesLoading = false, onBatch, onSectionChange, disabled }: {
  assignments: FacultyAttendanceAssignment[]
  sectionId: string
  batch: string
  batches: AcademicBatch[]
  batchesLoading?: boolean
  onBatch: (batch: string) => void
  onSectionChange: (sectionId: string) => void
  disabled: boolean
}) {
  const classes = registrationClasses(assignments)
  const selected = classes.find((item) => item.ids.includes(sectionId))
  const courses = [...new Set(classes.map((item) => item.course))]
  const branches = classes.filter((item) => item.course === selected?.course).filter((item, index, all) => all.findIndex((other) => other.programId === item.programId) === index)
  const sections = classes.filter((item) => item.programId === selected?.programId)
  const availableBatches = batches.filter((item) => item.is_active && item.program_id === selected?.programId)
  return <fieldset disabled={disabled} className="rounded-xl border border-[#26394e] bg-[#0d1c2c] p-5">
    <legend className="sr-only">Academic placement</legend>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <label className="text-sm text-slate-300">Course<select className={input} value={selected?.course ?? ''} onChange={(event) => { const next = classes.find((item) => item.course === event.target.value); if (next) onSectionChange(next.id) }}>
        {!selected && <option value="">Course unavailable</option>}{courses.map((course) => <option key={course} value={course}>{course}</option>)}
      </select></label>
      <label className="text-sm text-slate-300">Branch<select className={input} value={selected?.programId ?? ''} onChange={(event) => { const next = classes.find((item) => item.programId === event.target.value); if (next) onSectionChange(next.id) }}>
        {!selected && <option value="">Branch unavailable</option>}{branches.map((branch) => <option key={branch.programId} value={branch.programId}>{branch.branch}</option>)}
      </select></label>
      <label className="text-sm text-slate-300">Section<select className={input} value={selected?.id ?? ''} onChange={(event) => onSectionChange(event.target.value)}>
        {!selected && <option value="">Section unavailable</option>}{sections.map((section) => <option key={section.id} value={section.id}>{section.code}{sections.filter((other) => other.code === section.code).length > 1 && section.term ? ` · ${section.term}` : ''}</option>)}
      </select></label>
      <label className="text-sm text-slate-300">Batch<select className={input} value={availableBatches.some((item) => item.batch_id === batch) ? batch : ''} disabled={batchesLoading || !availableBatches.length} onChange={(event) => onBatch(event.target.value)} aria-describedby="registration-batch-hint">
        <option value="">{batchesLoading ? 'Loading batches…' : availableBatches.length ? 'Select batch' : 'No active batches'}</option>
        {availableBatches.map((item) => <option key={item.batch_id} value={item.batch_id}>{item.start_year}–{item.end_year}</option>)}
      </select></label>
    </div>
    <p id="registration-batch-hint" className="mt-3 text-xs text-slate-400">{!batchesLoading && !availableBatches.length ? 'No active batches are set up for this branch. Ask your administrator to add one in Academic Setup → Batches, then refresh batches.' : 'Choose an admission cohort created in Academic Setup, for example 2026–2030. Subjects can be assigned later.'}</p>
    {!selected && <p role="alert" className="mt-3 text-sm text-red-300">Course and branch details are unavailable for this class. Contact your administrator.</p>}
  </fieldset>
}

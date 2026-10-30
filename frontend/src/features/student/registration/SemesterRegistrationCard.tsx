import { useState } from 'react'
import type { StudentSemester } from '../../../types/semesterRegistration.ts'

export default function SemesterRegistrationCard({
  semester,
  busy,
  canManage,
  onComplete,
}: {
  semester: StudentSemester
  busy: boolean
  canManage: boolean
  onComplete: (id: string, options: string[]) => Promise<void>
}) {
  const [selected, setSelected] = useState<Record<string, string>>({})
  const required = semester.subjects.filter((subject) => subject.is_required)
  const optionIds = semester.groups.map((group) => selected[group.choice_group_id]).filter(Boolean)
  const subjectIds = new Set(required.map((subject) => subject.curriculum_subject_id))
  semester.groups.forEach((group) =>
    group.options
      .find((option) => option.choice_option_id === selected[group.choice_group_id])
      ?.curriculum_subject_ids.forEach((id) => subjectIds.add(id)),
  )
  const chosen = semester.subjects.filter((subject) => subjectIds.has(subject.curriculum_subject_id))
  const complete =
    optionIds.length === semester.groups.length &&
    chosen.length > 0 &&
    chosen.length === subjectIds.size &&
    chosen.every((subject) => subject.available)
  return (
    <article className="ui-panel p-5" aria-label={`${semester.program_semester_name} registration`}>
      <h2 className="text-section font-semibold">
        {semester.program_name} · {semester.program_semester_name}
      </h2>
      <p className="mt-2 text-muted">
        {semester.batch_name} · {semester.section_name} · {semester.term_name}
      </p>
      <p className="mt-1 text-sm text-muted">
        {semester.start_date} to {semester.end_date}
      </p>
      {semester.status === 'registered' ? (
        <div role="status" className="mt-5">
          <h3 className="font-semibold text-success">Registration complete</h3>
          <ul className="mt-3 list-disc pl-5">
            {semester.enrolled_subjects.map((subject) => (
              <li key={subject.course_id}>
                {subject.name} ({subject.code}){subject.credits !== null ? ` · ${subject.credits} credits` : ''}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <form
          className="mt-5 space-y-5"
          onSubmit={(event) => {
            event.preventDefault()
            if (complete && canManage && !busy) void onComplete(semester.semester_registration_id, optionIds)
          }}
        >
          <div>
            <h3 className="font-semibold">Common required subjects</h3>
            <ul className="mt-2 list-disc pl-5">
              {required.map((subject) => (
                <li key={subject.curriculum_subject_id}>
                  {subject.name}
                  {!subject.available ? ' — currently unavailable' : ''}
                </li>
              ))}
            </ul>
            {!required.length && <p className="text-sm text-muted">No common subjects configured.</p>}
          </div>
          {semester.groups.map((group) => (
            <fieldset className="space-y-3" key={group.choice_group_id} disabled={busy || !canManage}>
              <legend className="font-semibold">{group.name} — choose one complete option</legend>
              {group.options.map((option) => {
                const subjects = option.curriculum_subject_ids.map((id) =>
                  semester.subjects.find((subject) => subject.curriculum_subject_id === id),
                )
                const available = subjects.length > 0 && subjects.every((subject) => subject?.available)
                return (
                  <label
                    key={option.choice_option_id}
                    className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border border-control p-4 focus-within:ring-2 focus-within:ring-accent"
                  >
                    <input
                      className="mt-1 h-5 w-5 shrink-0 accent-accent"
                      type="radio"
                      name={group.choice_group_id}
                      value={option.choice_option_id}
                      checked={selected[group.choice_group_id] === option.choice_option_id}
                      disabled={!available}
                      onChange={() => setSelected({ ...selected, [group.choice_group_id]: option.choice_option_id })}
                    />
                    <span>
                      <span className="font-semibold">{option.name}</span>
                      <span className="mt-1 block text-sm text-muted">
                        {subjects.map((subject) => subject?.name ?? 'Subject unavailable').join(', ')}
                      </span>
                      {!available && (
                        <span className="mt-1 block text-sm text-warning">
                          Unavailable — a subject is not offered or has no seats.
                        </span>
                      )}
                    </span>
                  </label>
                )
              })}
            </fieldset>
          ))}
          {!complete && (
            <p className="text-sm text-muted">
              Choose an available option from each group. Every common subject and every subject in your selected
              options must be available.
            </p>
          )}
          <p className="text-sm text-muted">
            {chosen.length} subjects selected. Your selection is final after registration.
          </p>
          <button
            type="submit"
            className="min-h-11 rounded-lg bg-accent px-4 py-2 font-semibold text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy || !canManage || !complete}
          >
            {busy ? 'Please wait…' : 'Register selected subjects'}
          </button>
          {!canManage && (
            <p role="status" className="text-sm text-muted">
              You have read-only registration access.
            </p>
          )}
        </form>
      )}
    </article>
  )
}

import { useState } from 'react'
import type { Course } from '../../../../../types/academicSetup.ts'
import type { CurriculumSubject, CurriculumVersion, ProgramSemester } from '../../../../../types/academicStructure.ts'

interface Change {
  semester: string
  subject: string
  state: 'Added' | 'Removed' | 'Changed'
  details: string
}

function changesBetween(
  left: CurriculumVersion,
  right: CurriculumVersion,
  subjects: CurriculumSubject[],
  semesters: ProgramSemester[],
  courses: Course[],
): Change[] {
  const stageName = (id: string) =>
    semesters.find((item) => item.program_semester_id === id)?.name ?? 'Semester unavailable'
  const subjectName = (item: CurriculumSubject) =>
    item.subject_name || courses.find((course) => course.course_id === item.course_id)?.name || 'Subject unavailable'
  const mappings = (version: CurriculumVersion) =>
    new Map(
      subjects
        .filter((subject) => subject.curriculum_version_id === version.curriculum_version_id)
        .map((subject) => [`${subject.program_semester_id}:${subject.course_id}`, subject]),
    )
  const before = mappings(left)
  const after = mappings(right)
  const keys = new Set([...before.keys(), ...after.keys()])
  const result: Change[] = []
  for (const key of keys) {
    const oldSubject = before.get(key)
    const newSubject = after.get(key)
    const subject = newSubject ?? oldSubject!
    if (!oldSubject || !newSubject) {
      result.push({
        semester: stageName(subject.program_semester_id),
        subject: subjectName(subject),
        state: newSubject ? 'Added' : 'Removed',
        details: newSubject ? 'Added to the newer version' : 'Removed from the newer version',
      })
      continue
    }
    const fields: string[] = []
    if (oldSubject.course_type !== newSubject.course_type) fields.push('subject type')
    if (oldSubject.is_required !== newSubject.is_required) fields.push('required status')
    if (oldSubject.is_active !== newSubject.is_active) fields.push('active status')
    if (oldSubject.subject_code !== newSubject.subject_code) fields.push('subject code')
    if (oldSubject.subject_name !== newSubject.subject_name) fields.push('subject name')
    if (oldSubject.credits !== newSubject.credits) fields.push('credits')
    if (oldSubject.lecture_hours !== newSubject.lecture_hours) fields.push('lecture hours')
    if (oldSubject.tutorial_hours !== newSubject.tutorial_hours) fields.push('tutorial hours')
    if (oldSubject.practical_hours !== newSubject.practical_hours) fields.push('practical hours')
    if (fields.length)
      result.push({
        semester: stageName(newSubject.program_semester_id),
        subject: subjectName(newSubject),
        state: 'Changed',
        details: `Changed ${fields.join(', ')}`,
      })
  }
  return result.sort((a, b) => a.semester.localeCompare(b.semester) || a.subject.localeCompare(b.subject))
}

export default function CurriculumVersionCompare({
  versions,
  subjects,
  semesters,
  courses,
}: {
  versions: CurriculumVersion[]
  subjects: CurriculumSubject[]
  semesters: ProgramSemester[]
  courses: Course[]
}) {
  const published = versions.filter((item) => item.published_at)
  const comparable = published.filter((version) =>
    published.some(
      (other) =>
        other.program_id === version.program_id && other.curriculum_version_id !== version.curriculum_version_id,
    ),
  )
  const [leftId, setLeftId] = useState('')
  const left = comparable.find((item) => item.curriculum_version_id === leftId)
  const candidates = published.filter((item) => item.program_id === left?.program_id && item !== left)
  const [rightId, setRightId] = useState('')
  const right = candidates.find((item) => item.curriculum_version_id === rightId)
  const changes = left && right ? changesBetween(left, right, subjects, semesters, courses) : []
  if (comparable.length < 2) return <p>Publish another version of the same program to compare study plans.</p>
  return (
    <section aria-label="Compare curriculum versions" className="curriculum-version-compare">
      <h2>Compare versions</h2>
      <div className="structure-filters">
        <label>
          Earlier version
          <select
            aria-label="Earlier version"
            value={leftId}
            onChange={(event) => {
              setLeftId(event.target.value)
              setRightId('')
            }}
          >
            <option value="">Select a curriculum version</option>
            {comparable.map((item) => (
              <option key={item.curriculum_version_id} value={item.curriculum_version_id}>
                {item.name} · v{item.version}
              </option>
            ))}
          </select>
        </label>
        <label>
          Later version
          <select
            aria-label="Later version"
            value={rightId}
            disabled={!left}
            onChange={(event) => setRightId(event.target.value)}
          >
            <option value="">Select a version of the same program</option>
            {candidates.map((item) => (
              <option key={item.curriculum_version_id} value={item.curriculum_version_id}>
                {item.name} · v{item.version}
              </option>
            ))}
          </select>
        </label>
      </div>
      {left && right && (
        <div>
          <p>
            Comparing {left.name} · v{left.version} with {right.name} · v{right.version}.
          </p>
          {!changes.length ? (
            <p>No subject mapping changes between these versions.</p>
          ) : (
            <ul>
              {changes.map((change) => (
                <li key={`${change.semester}:${change.subject}:${change.state}`}>
                  <strong>{change.state}</strong> · {change.semester} · {change.subject} — {change.details}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

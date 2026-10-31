import type { CurriculumVersion, CurriculumSubject, ProgramSemester } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import { useStructureEditor } from '../../structure/useStructureEditor.ts'
import { COURSE_TYPE_LABELS } from '../../forms/academicCourseTypes.ts'
import SemesterSubjectDrawer from './SemesterSubjectDrawer.tsx'
import { studyPlanCanChange } from './studyPlanModel.ts'
import type { StudyPlanChoicesState } from './useStudyPlanChoices.ts'
import SemesterChoices from '../choices/SemesterChoices.tsx'
import SemesterSubjectList from './SemesterSubjectList.tsx'
import SemesterSettings from '../semesters/SemesterSettings.tsx'

export default function SemesterCard({
  state,
  version,
  semester,
  number,
  subjects,
  choices,
}: {
  state: AcademicStructureState
  version: CurriculumVersion
  semester?: ProgramSemester
  number: number
  subjects: CurriculumSubject[]
  choices: StudyPlanChoicesState
}) {
  const name = `Semester ${number}`
  const included = subjects.filter((subject) => subject.is_active).length
  const editable = studyPlanCanChange(state, version) && Boolean(semester?.is_active)
  const editor = useStructureEditor(state, 'curriculum_subjects', {
    curriculum_version_id: version.curriculum_version_id,
    program_semester_id: semester?.program_semester_id ?? '',
  })
  const used = new Set(subjects.map((subject) => subject.course_id))
  const fields = editor.fields
    .filter((field) =>
      ['course_id', 'course_type', 'is_required', ...(editor.panel?.row ? ['is_active'] : [])].includes(field.key),
    )
    .map((field) => ({
      ...field,
      label:
        field.key === 'is_required'
          ? 'Every student must take this subject'
          : field.key === 'is_active'
            ? 'Include in study plan'
            : field.label,
      help:
        field.key === 'is_required'
          ? 'Leave unchecked if students will choose it through a subject option group.'
          : field.help,
      options:
        field.key === 'course_id' && !editor.panel?.row
          ? field.options?.filter((option) => !used.has(option.value))
          : field.key === 'course_type'
            ? field.options?.map((option) => ({
                ...option,
                label: COURSE_TYPE_LABELS[option.value as keyof typeof COURSE_TYPE_LABELS],
              }))
            : field.options,
    }))
  const canAdd =
    editable && editor.canManage && Boolean(fields.find((field) => field.key === 'course_id')?.options?.length)
  return (
    <section className="study-plan-semester" aria-label={`${name} subjects`}>
      <header>
        <div className="study-plan-semester-title">
          <h3>{name}</h3>
          <p className="study-plan-semester-count">
            {included} {included === 1 ? 'subject' : 'subjects'} included
          </p>
          {semester && (
            <p className="study-plan-semester-count">
              {semester.name} · {semester.code}
              {!semester.is_active && ' · Inactive'}
            </p>
          )}
        </div>
        {semester && version.status === 'draft' && (
          <SemesterSettings state={state} version={version} semester={semester} trackDraft={choices.trackDraft} />
        )}
        {version.status === 'draft' && (
          <button
            type="button"
            className="academic-secondary-button"
            disabled={!canAdd || editor.saving}
            onClick={() => editor.open('add')}
          >
            Add subject <span className="sr-only">to {name}</span>
          </button>
        )}
      </header>
      {!semester ? (
        <p>This semester has not been set up yet. Use semester setup above to create it here.</p>
      ) : !semester.is_active ? (
        <p>This program semester is inactive. Existing subjects are shown below.</p>
      ) : !subjects.length ? (
        <p>No subjects yet. Choose what students will study in {name.toLowerCase()}.</p>
      ) : null}
      {[true, false].map((compulsory) => (
        <SemesterSubjectList
          key={String(compulsory)}
          state={state}
          subjects={subjects.filter((subject) => subject.is_required === compulsory)}
          semesterName={name}
          compulsory={compulsory}
          showEdit={version.status === 'draft'}
          canEdit={editable && editor.canManage && !editor.saving}
          onEdit={(subject) => editor.open('edit', subject)}
        />
      ))}
      {semester && (
        <SemesterChoices
          structure={state}
          state={choices}
          version={version}
          semester={semester}
          onDraftChange={choices.trackDraft}
        />
      )}
      {canAdd === false && editable && state.canManage('curriculum_subjects') && (
        <p>All available subjects are already listed here, or there are no active subjects to add.</p>
      )}
      {editor.notice && <p role="status">Subject saved in {name.toLowerCase()}.</p>}
      {editor.panel && (
        <SemesterSubjectDrawer
          editor={{ ...editor, fields, canManage: editable && editor.canManage }}
          semesterName={name}
          curriculumName={version.name}
        />
      )}
    </section>
  )
}

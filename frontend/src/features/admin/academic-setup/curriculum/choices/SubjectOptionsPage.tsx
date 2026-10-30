import { useState } from 'react'
import { deleteChoiceGroup, saveChoiceGroup } from '../../../../../services/academics/semesterRegistration.ts'
import { useAcademicStructure, type StructureContext } from '../../structure/useAcademicStructure.ts'
import StructureState from '../../structure/StructureState.tsx'
import { useRegistrationAdmin } from '../../registration/useRegistrationAdmin.ts'
import { useChoiceEditor } from './useChoiceEditor.ts'
import ChoiceGroupForm from './ChoiceGroupForm.tsx'
import '../../registration/registration.css'
import StructureRecordsPage from '../../structure/StructureRecordsPage.tsx'

export default function SubjectOptionsPage({
  context,
  onContinue,
}: {
  context: StructureContext
  onContinue?: () => void
}) {
  const structure = useAcademicStructure(context)
  const state = useRegistrationAdmin(context)
  const editor = useChoiceEditor()
  const [deleteId, setDeleteId] = useState<string>()
  const [managingSubjects, setManagingSubjects] = useState(false)
  const groups = state.data?.groups ?? []
  const canWrite = state.data?.can_manage_choices && !state.busy && !structure.busy
  async function save() {
    if (await state.save(() => saveChoiceGroup(context.accessToken, editor.draft, editor.editingId))) editor.reset()
  }
  async function remove() {
    if (deleteId && (await state.save(() => deleteChoiceGroup(context.accessToken, deleteId)))) {
      if (editor.editingId === deleteId) editor.reset()
      setDeleteId(undefined)
    }
  }
  if (managingSubjects)
    return (
      <StructureRecordsPage
        context={context}
        entity="curriculum_subjects"
        title="Semester Subject Mappings"
        onOverview={() => setManagingSubjects(false)}
        defaults={{
          curriculum_version_id: editor.draft.curriculum_version_id,
          program_semester_id: editor.draft.program_semester_id,
          is_required: false,
          course_type: 'elective',
        }}
        filter={(row) =>
          'curriculum_version_id' in row &&
          'program_semester_id' in row &&
          row.curriculum_version_id === editor.draft.curriculum_version_id &&
          row.program_semester_id === editor.draft.program_semester_id
        }
      >
        <div className="registration-panel">
          <p>
            Add the subjects for this curriculum semester. Leave Required Subject unchecked for subjects belonging to an
            option. Check it for subjects every student must take.
          </p>
          <p>Your option group draft is kept while you add or edit these mappings.</p>
          <button type="button" className="academic-secondary-button" onClick={() => setManagingSubjects(false)}>
            Back to option group
          </button>
        </div>
      </StructureRecordsPage>
    )
  return (
    <section className="semester-registration" aria-label="Curriculum subject options">
      <h1>Subject Options</h1>
      <p>Keep common subjects required. Group the remaining subjects into complete alternatives before publishing.</p>
      <StructureState state={structure} />
      {state.query.isPending && <p role="status">Loading subject options…</p>}
      {state.error instanceof Error && (
        <div role="alert">
          <p>{state.error.message}</p>
          <button type="button" className="academic-secondary-button" onClick={() => void state.query.refetch()}>
            Retry
          </button>
        </div>
      )}
      {state.notice && <p role="status">{state.notice}</p>}
      {state.notice && onContinue && (
        <button type="button" className="academic-primary-button" onClick={onContinue}>
          Next: review and publish curriculum
        </button>
      )}
      {state.data && !groups.length && <p>No subject option groups yet.</p>}
      {groups.map((group) => {
        const version = structure.structure?.records.curriculum_versions?.find(
          (item) => item.curriculum_version_id === group.curriculum_version_id,
        )
        const stage = structure.structure?.records.program_semesters?.find(
          (item) => item.program_semester_id === group.program_semester_id,
        )
        return (
          <article key={group.choice_group_id} className="registration-panel">
            <h2>{group.name}</h2>
            <p>
              {version?.name} · {stage?.name} · {version?.status}
            </p>
            <div className="registration-grid">
              {group.options.map((option) => (
                <div key={option.choice_option_id}>
                  <h3>{option.name}</h3>
                  <ul>
                    {option.curriculum_subject_ids.map((id) => {
                      const mapping = structure.structure?.records.curriculum_subjects?.find(
                        (item) => item.curriculum_subject_id === id,
                      )
                      const subject = structure.catalogue?.records.courses?.find(
                        (item) => item.course_id === mapping?.course_id,
                      )
                      return <li key={id}>{subject?.name ?? 'Subject unavailable'}</li>
                    })}
                  </ul>
                </div>
              ))}
            </div>
            {version?.status === 'draft' && (
              <div className="registration-actions">
                <button
                  type="button"
                  className="academic-secondary-button"
                  disabled={!canWrite}
                  onClick={() => editor.edit(group)}
                >
                  Edit group
                </button>
                <button
                  type="button"
                  className="academic-secondary-button"
                  disabled={!canWrite}
                  onClick={() => setDeleteId(group.choice_group_id)}
                >
                  Delete group
                </button>
              </div>
            )}
            {deleteId === group.choice_group_id && (
              <div role="group" aria-label="Confirm option group deletion">
                <p>Delete this draft option group?</p>
                <div className="registration-actions">
                  <button
                    type="button"
                    className="academic-secondary-button"
                    disabled={!canWrite}
                    onClick={() => void remove()}
                  >
                    Confirm delete
                  </button>
                  <button
                    type="button"
                    className="academic-secondary-button"
                    disabled={state.saving}
                    onClick={() => setDeleteId(undefined)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </article>
        )
      })}
      {state.data?.can_manage_choices && (
        <ChoiceGroupForm
          editor={editor}
          structure={structure}
          disabled={!canWrite}
          onSubmit={save}
          onManageSubjects={() => setManagingSubjects(true)}
        />
      )}
    </section>
  )
}

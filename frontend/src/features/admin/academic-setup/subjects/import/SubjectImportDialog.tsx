import { X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../../workspace/useWorkspaceDialog.ts'
import { useSubjectImport } from './useSubjectImport.ts'
import SubjectImportPanel from './SubjectImportPanel.tsx'
import './subject-import.css'

type Props = Parameters<typeof useSubjectImport>[0] & { onClose: () => void }

/** Each opening starts a fresh import; the state lives only while the dialog is open. */
export default function SubjectImportDialog({ onClose, ...options }: Props) {
  const state = useSubjectImport(options)
  const ref = useWorkspaceDialog('.subjects-page h1')
  const pending = state.valid.length - state.done.length
  const retry = state.failed.length > 0
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className="subject-drawer subject-import-drawer"
      aria-modal="true"
      aria-labelledby="subject-import-title"
      aria-describedby="subject-import-description"
      aria-busy={state.running}
      onCancel={(event) => {
        event.preventDefault()
        if (!state.running) onClose()
      }}
    >
      <header>
        <div>
          <h2 id="subject-import-title">Import Subjects</h2>
          <p id="subject-import-description">
            Add many subjects from a CSV file. Choose a draft curriculum to also place them in its semesters.
          </p>
        </div>
        <button type="button" aria-label="Close subject import" disabled={state.running} onClick={onClose}>
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="subject-drawer-body subject-import-body">
        <div className="subject-import-choices">
          <label>
            <span>
              Department <span aria-hidden="true">*</span>
            </span>
            <select
              value={state.departmentId}
              disabled={state.running}
              onChange={(event) => state.setDepartmentId(event.target.value)}
            >
              <option value="">Select department</option>
              {state.departments.map((item) => (
                <option key={item.department_id} value={item.department_id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Place in draft curriculum (optional)</span>
            <select
              value={state.curriculumId}
              disabled={state.running || !state.departmentId}
              onChange={(event) => state.setCurriculumId(event.target.value)}
            >
              <option value="">Only add to the subject catalogue</option>
              {state.curricula.map((item) => (
                <option key={item.curriculum_version_id} value={item.curriculum_version_id}>
                  {item.name} · v{item.version}
                </option>
              ))}
            </select>
            <small>
              {state.curriculumId
                ? 'Rows with a semester are added to that semester of the curriculum.'
                : 'The semester column is used only when a draft curriculum is chosen.'}
            </small>
          </label>
        </div>
        <SubjectImportPanel state={state} />
      </div>
      <footer>
        <button type="button" className="academic-secondary-button" disabled={state.running} onClick={onClose}>
          {state.done.length && !pending ? 'Done' : 'Cancel'}
        </button>
        <button
          type="button"
          className="academic-primary-button"
          disabled={state.running || !state.departmentId || pending === 0}
          onClick={() => void state.start()}
        >
          {state.running
            ? 'Importing…'
            : retry
              ? `Retry ${state.failed.length} failed row${state.failed.length === 1 ? '' : 's'}`
              : `Import ${pending} row${pending === 1 ? '' : 's'}`}
        </button>
      </footer>
    </dialog>
  )
}

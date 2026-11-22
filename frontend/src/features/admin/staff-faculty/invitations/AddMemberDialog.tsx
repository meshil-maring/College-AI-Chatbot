import { X } from 'lucide-react'
import { useEffect, useId, useRef, type FormEvent } from 'react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MemberInvitationCreate } from '../../../../types/admin.ts'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import { BUTTON_CLASS, PRIMARY_BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import BasicDetailsStep from './add-member/BasicDetailsStep.tsx'
import ReviewStep from './add-member/ReviewStep.tsx'
import RoleDetailsStep from './add-member/RoleDetailsStep.tsx'
import { STEPS, type MemberDraft } from './add-member/memberDraft.ts'
import { useAddMemberDraft } from './add-member/useAddMemberDraft.ts'

/** Details known before the form opens, such as an expired invitation's. */
export type InvitationDraft = Partial<MemberDraft>

interface Props {
  departments: Department[]
  initial?: InvitationDraft
  sending: boolean
  /** Resolves to an error message to show, or null when the invitation was sent. */
  onSubmit: (request: MemberInvitationCreate) => Promise<string | null>
  onClose: () => void
}

/**
 * Add New User: basic details, then role details, then review. The person is
 * invited by email and sets their own password; their employee profile is
 * saved when they accept.
 */
export default function AddMemberDialog({ departments, initial = {}, sending, onSubmit, onClose }: Props) {
  const ref = useWorkspaceDialog('#staff-faculty-add-member')
  const id = useId()
  const listed = departments.some((department) => department.department_id === initial.department_id)
  const model = useAddMemberDraft({ ...initial, department_id: listed ? initial.department_id : '' }, onSubmit, onClose)
  const heading = useRef<HTMLHeadingElement>(null)
  const last = model.step === STEPS.length - 1

  // Move focus to the step heading so screen readers announce the new step.
  const first = useRef(true)
  useEffect(() => {
    if (first.current) first.current = false
    else heading.current?.focus()
  }, [model.step])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (last) void model.send()
    else model.next()
  }

  return (
    <dialog
      ref={ref}
      aria-labelledby={`${id}-title`}
      onCancel={(event) => {
        event.preventDefault()
        if (!sending) onClose()
      }}
      className="m-auto w-[min(640px,100vw)] rounded-xl border border-line bg-surface p-0 text-content shadow-overlay backdrop:bg-[var(--ui-overlay)]"
    >
      <form noValidate onSubmit={submit} className="flex max-h-[min(760px,100dvh)] flex-col">
        <header className="flex items-start gap-3 border-b border-line p-5">
          <div className="mr-auto">
            <h2 id={`${id}-title`} className="text-section font-semibold">
              Add Staff or Faculty
            </h2>
            <ol aria-label="Steps" className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
              {STEPS.map((label, index) => (
                <li
                  key={label}
                  aria-current={index === model.step ? 'step' : undefined}
                  className={index === model.step ? 'font-semibold text-content' : 'text-muted'}
                >
                  {index + 1}. {label}
                </li>
              ))}
            </ol>
          </div>
          <button
            type="button"
            aria-label="Close"
            disabled={sending}
            onClick={onClose}
            className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg hover:bg-hover"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </header>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          <h3 ref={heading} tabIndex={-1} className="text-sm font-semibold text-content outline-none">
            Step {model.step + 1} of {STEPS.length}: {STEPS[model.step]}
          </h3>
          {model.serverError ? (
            <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
              {model.serverError}
            </p>
          ) : null}
          {model.step === 0 ? <BasicDetailsStep model={model} idPrefix={id} /> : null}
          {model.step === 1 ? <RoleDetailsStep model={model} idPrefix={id} departments={departments} /> : null}
          {model.step === 2 ? <ReviewStep draft={model.draft} departments={departments} /> : null}
        </div>
        <footer className="flex flex-wrap justify-end gap-2 border-t border-line p-5">
          <button type="button" disabled={sending} onClick={onClose} className={`${BUTTON_CLASS} mr-auto`}>
            Cancel
          </button>
          {model.step > 0 ? (
            <button type="button" disabled={sending} onClick={model.back} className={BUTTON_CLASS}>
              Back
            </button>
          ) : null}
          <button
            type="submit"
            disabled={sending || (model.step === 1 && departments.length === 0)}
            className={PRIMARY_BUTTON_CLASS}
          >
            {last ? (sending ? 'Sending…' : 'Send invitation') : 'Next'}
          </button>
        </footer>
      </form>
    </dialog>
  )
}

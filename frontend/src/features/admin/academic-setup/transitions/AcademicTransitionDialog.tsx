import { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import type { AcademicRecord } from '../../../../types/academicSetup.ts'
import { academicButtonClass } from '../forms/academicFormControls.ts'

export default function AcademicTransitionDialog({
  record,
  onConfirm,
  onCancel,
}: {
  record: AcademicRecord
  onConfirm: () => void
  onCancel: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const label = record.name
  const action = record.is_active ? 'deactivation' : 'activation'
  useEffect(() => {
    const dialog = ref.current
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    return () => {
      if (dialog?.open) dialog.close?.()
    }
  }, [])
  return (
    <dialog
      ref={ref}
      className="academic-transition-dialog"
      aria-labelledby="academic-transition-title"
      aria-describedby="academic-transition-description"
      onCancel={onCancel}
    >
      <AlertTriangle aria-hidden="true" />
      <h2 id="academic-transition-title">Confirm {action}</h2>
      <p id="academic-transition-description">
        {record.is_active ? 'Deactivate' : 'Activate'} “{label}”?
        {record.is_active && ' Existing records will be retained. Active dependencies may prevent this change.'}
        {'is_current' in record &&
          record.is_current &&
          record.is_active &&
          ' This will also clear its current designation.'}
      </p>
      <div>
        <button type="button" className={academicButtonClass} onClick={onCancel} autoFocus>
          Cancel
        </button>
        <button type="button" className={`${academicButtonClass} academic-confirm-transition`} onClick={onConfirm}>
          Confirm {action}
        </button>
      </div>
    </dialog>
  )
}

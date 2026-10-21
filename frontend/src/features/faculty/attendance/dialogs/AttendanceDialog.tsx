import { GraduationCap } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Glyph } from '../shared/AttendanceWorkspaceUi.tsx'
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string
  onClose: () => void
  children: React.ReactNode
  wide?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    ref.current?.focus()
    return () => previous?.focus()
  }, [])
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onKeyDown={(event) => {
          if (event.key === 'Escape') onClose()
          if (event.key === 'Tab') {
            const nodes = ref.current?.querySelectorAll<HTMLElement>(
              'button:not(:disabled), input:not(:disabled), select:not(:disabled), summary',
            )
            if (!nodes?.length) {
              event.preventDefault()
              return
            }
            const first = nodes[0],
              last = nodes[nodes.length - 1]
            if (event.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) {
              event.preventDefault()
              last.focus()
            } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === ref.current)) {
              event.preventDefault()
              first.focus()
            }
          }
        }}
        className={`max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-[#2c455e] bg-[#0d1c2c] p-5 shadow-2xl outline-none ${wide ? 'max-w-2xl' : 'max-w-lg'}`}
      >
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <button
            type="button"
            aria-label={`Close ${title}`}
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-[#142638] hover:text-white"
          >
            <Glyph name="close" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function NoAssignmentWorkflow({
  action,
  onNavigateAssignments,
  onClose,
}: {
  action: string
  onNavigateAssignments?: () => void
  onClose: () => void
}) {
  return (
    <div className="py-7 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#17293d] text-[#ffc72c]">
        <GraduationCap aria-hidden="true" size={28} strokeWidth={1.7} />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-white">No Active Assignments</h3>
      <p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-slate-400">
        You need an active course and section assignment before you can {action}. Ask your administrator to assign a
        section, then return here.
      </p>
      <div className="mt-4 flex justify-center gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-md border border-[#2c455e] px-3 py-1.5 text-[11px] font-semibold text-slate-300 hover:bg-[#142638]"
        >
          Close
        </button>
        {onNavigateAssignments ? (
          <button
            type="button"
            onClick={onNavigateAssignments}
            className="rounded-md bg-[#ffc72c] px-3 py-1.5 text-[11px] font-bold text-[#101820] hover:bg-[#ffd65d]"
          >
            View My Sections
          </button>
        ) : null}
      </div>
    </div>
  )
}

export function ModalActions({
  onCancel,
  onSubmit,
  submitLabel,
  saving,
}: {
  onCancel: () => void
  onSubmit: () => void
  submitLabel: string
  saving: boolean
}) {
  return (
    <div className="mt-5 flex justify-end gap-2 border-t border-[#1e3348] pt-4">
      <button
        type="button"
        onClick={onCancel}
        className="rounded-lg border border-[#2c455e] px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-[#142638]"
      >
        Cancel
      </button>
      <button
        type="button"
        disabled={saving}
        onClick={onSubmit}
        className="rounded-lg bg-[#ffc72c] px-4 py-2 text-xs font-bold text-[#101820] disabled:opacity-50"
      >
        {saving ? 'Working…' : submitLabel}
      </button>
    </div>
  )
}

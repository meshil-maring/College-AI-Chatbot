import { useEffect, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../../workspace/useWorkspaceDialog.ts'

export default function CurriculumDrawerFrame({
  title,
  description,
  onClose,
  busy = false,
  alert = false,
  initialFocusSelector,
  children,
  footer,
}: {
  title: string
  description: string
  onClose: () => void
  busy?: boolean
  alert?: boolean
  initialFocusSelector?: string
  children: ReactNode
  footer: ReactNode
}) {
  const ref = useWorkspaceDialog('.curriculum-page h1')
  useEffect(() => {
    if (alert) ref.current?.querySelector<HTMLElement>('footer button')?.focus()
    else if (initialFocusSelector) ref.current?.querySelector<HTMLElement>(initialFocusSelector)?.focus()
  }, [alert, initialFocusSelector, ref])
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className="curriculum-drawer"
      aria-modal="true"
      role={alert ? 'alertdialog' : undefined}
      aria-labelledby="curriculum-drawer-title"
      aria-describedby="curriculum-drawer-description"
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
    >
      <header>
        <div>
          <h2 id="curriculum-drawer-title">{title}</h2>
          <p id="curriculum-drawer-description">{description}</p>
        </div>
        <button type="button" aria-label="Close curriculum drawer" disabled={busy} onClick={onClose}>
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="curriculum-drawer-body">{children}</div>
      <footer>{footer}</footer>
    </dialog>
  )
}

import { useEffect, useRef, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { useWorkspaceDialog } from '../../workspace/useWorkspaceDialog.ts'

export default function ResourceDrawerFrame({
  title,
  busy,
  dirty,
  onClose,
  onReload,
  children,
}: {
  title: string
  busy: boolean
  dirty: boolean
  onClose: () => void
  onReload?: () => Promise<void>
  children: ReactNode
}) {
  const ref = useWorkspaceDialog('.learning-resources-page')
  const [confirmation, setConfirmation] = useState<'close' | 'reload' | null>(null)
  const keep = useRef<HTMLButtonElement>(null)
  const previous = useRef<HTMLElement | null>(null)
  useEffect(() => {
    if (confirmation) keep.current?.focus()
    else previous.current?.focus()
  }, [confirmation])
  function request(action: 'close' | 'reload') {
    if (busy) return
    if (dirty) {
      previous.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
      setConfirmation(action)
    } else if (action === 'close') onClose()
    else void onReload?.()
  }
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className="resource-drawer"
      aria-modal="true"
      role={confirmation ? 'alertdialog' : undefined}
      aria-labelledby="resource-drawer-title"
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault()
        if (!busy) {
          if (confirmation) setConfirmation(null)
          else request('close')
        }
      }}
    >
      <header className="lr-drawer-heading">
        <div>
          <p className="ui-eyebrow">Learning Resources</p>
          <h2 id="resource-drawer-title">{confirmation ? 'Discard unsaved changes?' : title}</h2>
        </div>
        <button
          type="button"
          className="lr-icon-button"
          aria-label="Close resource drawer"
          disabled={busy}
          onClick={() => (confirmation ? setConfirmation(null) : request('close'))}
        >
          <X size={20} aria-hidden="true" />
        </button>
      </header>
      <div className="lr-drawer-body">
        {confirmation && (
          <section className="lr-confirm" aria-label="Unsaved resource changes">
            <p>
              {confirmation === 'reload'
                ? 'Loading the latest revision replaces your unsaved entries and file selection.'
                : 'Your unsaved entries and file selection will be discarded. Saved drafts and uploaded files are retained.'}
            </p>
            <div className="lr-actions">
              <button
                ref={keep}
                type="button"
                className="lr-secondary"
                disabled={busy}
                onClick={() => setConfirmation(null)}
              >
                Keep editing
              </button>
              <button
                type="button"
                className="lr-danger-button"
                disabled={busy}
                onClick={() => {
                  if (confirmation === 'close') onClose()
                  else void onReload?.().then(() => setConfirmation(null))
                }}
              >
                {confirmation === 'reload' ? 'Discard entries and reload' : 'Discard and close'}
              </button>
            </div>
          </section>
        )}
        <div hidden={confirmation !== null}>{children}</div>
      </div>
      {!confirmation && (
        <footer className="lr-drawer-footer">
          {onReload && (
            <button type="button" className="lr-secondary" disabled={busy} onClick={() => request('reload')}>
              Reload latest
            </button>
          )}
          <button type="button" className="lr-secondary" disabled={busy} onClick={() => request('close')}>
            Close
          </button>
        </footer>
      )}
    </dialog>
  )
}

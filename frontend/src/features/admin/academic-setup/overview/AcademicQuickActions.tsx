import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Zap } from 'lucide-react'
import type { AcademicCatalogue, AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicQuickLinks from './AcademicQuickLinks.tsx'

export default function AcademicQuickActions({
  catalogue,
  busy,
  onCreate,
}: {
  catalogue?: AcademicCatalogue
  busy: boolean
  onCreate: (entity: AcademicEntity) => void
}) {
  const ref = useRef<HTMLDetailsElement>(null)
  const [open, setOpen] = useState(false)
  function close() {
    if (ref.current) ref.current.open = false
    setOpen(false)
  }
  useEffect(() => {
    if (!open) return
    function dismiss(event: PointerEvent) {
      if (event.target instanceof Node && !ref.current?.contains(event.target)) close()
    }
    function dismissWithEscape(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      close()
      ref.current?.querySelector('summary')?.focus()
    }
    document.addEventListener('pointerdown', dismiss)
    document.addEventListener('keydown', dismissWithEscape, true)
    return () => {
      document.removeEventListener('pointerdown', dismiss)
      document.removeEventListener('keydown', dismissWithEscape, true)
    }
  }, [open])
  return (
    <details ref={ref} className="academic-quick-actions" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="academic-primary-button" aria-expanded={open}>
        <Zap aria-hidden="true" /> Quick Actions <ChevronDown aria-hidden="true" />
      </summary>
      {open && (
        <div className="academic-action-popover">
          <AcademicQuickLinks
            catalogue={catalogue}
            busy={busy}
            compact
            onCreate={(entity) => {
              close()
              onCreate(entity)
            }}
          />
        </div>
      )}
    </details>
  )
}

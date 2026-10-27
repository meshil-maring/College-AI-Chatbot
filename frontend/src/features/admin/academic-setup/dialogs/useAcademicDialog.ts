import { useEffect, useRef } from 'react'

export function useAcademicDialog(fallbackSelector: string) {
  const ref = useRef<HTMLDialogElement>(null)
  const trigger = useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null)
  useEffect(() => {
    const dialog = ref.current
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    function trapFocus(event: KeyboardEvent) {
      if (event.key !== 'Tab' || !dialog) return
      const controls = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex="0"]',
        ),
      ).filter((control) => control.getClientRects().length > 0)
      if (!controls.length) {
        event.preventDefault()
        dialog.focus()
        return
      }
      const first = controls[0]
      const last = controls.at(-1)
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
    dialog?.addEventListener('keydown', trapFocus)
    return () => {
      dialog?.removeEventListener('keydown', trapFocus)
      if (dialog?.open) dialog.close?.()
      document.body.style.overflow = previousOverflow
      if (trigger.current?.isConnected) trigger.current.focus()
      else document.querySelector<HTMLElement>(fallbackSelector)?.focus()
    }
  }, [fallbackSelector])
  return ref
}

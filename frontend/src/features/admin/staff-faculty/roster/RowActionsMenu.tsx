import { ChevronDown } from 'lucide-react'
import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { BUTTON_CLASS } from '../StaffFacultyUI.tsx'

export interface RowAction {
  key: string
  label: string
  icon?: ReactNode
  /** Destructive actions are separated from the others and shown in danger colors. */
  danger?: boolean
  onSelect: () => void
}

interface Props {
  /** Who the actions belong to, for the button's accessible name. */
  label: string
  actions: RowAction[]
  disabled: boolean
  /** Shown on the button while one of this row's actions is saving. */
  busyText?: string | null
}

const MENU_WIDTH = 208

/**
 * One "Actions" button per roster row that opens a menu. The menu is portalled
 * to the page body with fixed positioning so the table's horizontal scroll
 * never clips it. Keyboard: arrows move, Home/End jump, Escape or Tab closes.
 */
export default function RowActionsMenu({ label, actions, disabled, busyText }: Props) {
  const [open, setOpen] = useState(false)
  const [focusIndex, setFocusIndex] = useState(0)
  const [position, setPosition] = useState<{ top: number; left: number }>({ top: 0, left: 0 })
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const menuId = useId()

  function show(index: number) {
    setFocusIndex(index)
    setOpen(true)
  }

  function close(returnFocus = true) {
    setOpen(false)
    if (returnFocus) buttonRef.current?.focus()
  }

  // Place below the button, right-aligned; flip above when there is no room.
  useLayoutEffect(() => {
    if (!open || !buttonRef.current) return
    const rect = buttonRef.current.getBoundingClientRect()
    const height = menuRef.current?.offsetHeight ?? 0
    const below = rect.bottom + 4
    const top = below + height > window.innerHeight && rect.top - height - 4 > 0 ? rect.top - height - 4 : below
    const left = Math.max(8, Math.min(rect.right - MENU_WIDTH, window.innerWidth - MENU_WIDTH - 8))
    setPosition({ top, left })
  }, [open])

  useEffect(() => {
    if (!open) return
    menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]')[focusIndex]?.focus()
  }, [open, focusIndex])

  // Clicking elsewhere, scrolling or resizing closes the menu.
  useEffect(() => {
    if (!open) return
    function outside(event: MouseEvent) {
      const target = event.target as Node
      if (!menuRef.current?.contains(target) && !buttonRef.current?.contains(target)) close(false)
    }
    function dismiss() {
      close(false)
    }
    document.addEventListener('mousedown', outside)
    window.addEventListener('resize', dismiss)
    window.addEventListener('scroll', dismiss, true)
    return () => {
      document.removeEventListener('mousedown', outside)
      window.removeEventListener('resize', dismiss)
      window.removeEventListener('scroll', dismiss, true)
    }
  }, [open])

  function onMenuKey(event: KeyboardEvent) {
    const last = actions.length - 1
    const moves: Record<string, number> = {
      ArrowDown: focusIndex >= last ? 0 : focusIndex + 1,
      ArrowUp: focusIndex <= 0 ? last : focusIndex - 1,
      Home: 0,
      End: last,
    }
    if (event.key in moves) {
      event.preventDefault()
      setFocusIndex(moves[event.key])
    } else if (event.key === 'Escape') {
      event.preventDefault()
      close()
    } else if (event.key === 'Tab') {
      close(false)
    }
  }

  function select(action: RowAction) {
    // Focus returns to the button first, so a dialog opened next restores it on close.
    close()
    action.onSelect()
  }

  if (actions.length === 0) return null
  const firstDanger = actions.findIndex((action) => action.danger)

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-label={`Actions for ${label}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        disabled={disabled}
        onClick={() => (open ? close() : show(0))}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault()
            show(event.key === 'ArrowDown' ? 0 : actions.length - 1)
          }
        }}
        className={BUTTON_CLASS}
      >
        {busyText ?? 'Actions'}
        <ChevronDown aria-hidden="true" className={`size-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open
        ? createPortal(
            <div
              ref={menuRef}
              id={menuId}
              role="menu"
              aria-label={`Actions for ${label}`}
              onKeyDown={onMenuKey}
              style={{ top: position.top, left: position.left, width: MENU_WIDTH }}
              className="fixed z-50 rounded-lg border border-line bg-raised p-1 shadow-overlay"
            >
              {actions.map((action, index) => (
                <div key={action.key}>
                  {index === firstDanger && index > 0 ? (
                    <div role="separator" className="my-1 border-t border-line" />
                  ) : null}
                  <button
                    type="button"
                    role="menuitem"
                    tabIndex={index === focusIndex ? 0 : -1}
                    onClick={() => select(action)}
                    onMouseEnter={() => setFocusIndex(index)}
                    className={`flex min-h-10 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium focus:outline-none ${
                      action.danger
                        ? 'text-danger hover:bg-danger-bg focus:bg-danger-bg'
                        : 'text-content hover:bg-hover focus:bg-hover'
                    }`}
                  >
                    {action.icon}
                    {action.label}
                  </button>
                </div>
              ))}
            </div>,
            document.body,
          )
        : null}
    </>
  )
}

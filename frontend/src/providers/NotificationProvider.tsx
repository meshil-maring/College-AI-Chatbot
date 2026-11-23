import type { CSSProperties } from 'react'
import { Toaster } from 'sonner'

/**
 * The application's only toast viewport. Mounted once in `main.tsx`; every
 * dashboard shares it through `lib/notifications/notification.ts`.
 *
 * Sonner's rich colours are mapped onto the design-system status tokens so
 * toasts match badges and inline messages in every workspace.
 */
const toasterTheme = {
  '--normal-bg': 'var(--ui-surface-raised)',
  '--normal-border': 'var(--ui-border)',
  '--normal-text': 'var(--ui-text)',
  '--normal-bg-hover': 'var(--ui-surface-hover)',
  '--normal-border-hover': 'var(--ui-border-control)',
  '--success-bg': 'var(--ui-success-bg)',
  '--success-border': 'var(--ui-success)',
  '--success-text': 'var(--ui-success)',
  '--error-bg': 'var(--ui-danger-bg)',
  '--error-border': 'var(--ui-danger)',
  '--error-text': 'var(--ui-danger)',
  '--warning-bg': 'var(--ui-warning-bg)',
  '--warning-border': 'var(--ui-warning)',
  '--warning-text': 'var(--ui-warning)',
  '--info-bg': 'var(--ui-info-bg)',
  '--info-border': 'var(--ui-info)',
  '--info-text': 'var(--ui-info)',
  fontFamily: 'var(--ui-font-sans)',
} as CSSProperties

export function NotificationProvider() {
  return (
    <Toaster
      theme="dark"
      position="top-right"
      richColors
      closeButton
      // Older toasts collapse behind the newest so feedback never covers
      // the page header controls; hovering expands the stack.
      visibleToasts={3}
      // Clear the 68px workspace top bar so header controls stay usable.
      offset={{ top: 80, right: 16 }}
      mobileOffset={{ top: 76, left: 16, right: 16 }}
      containerAriaLabel="Notifications"
      style={toasterTheme}
      toastOptions={{ closeButtonAriaLabel: 'Dismiss notification' }}
    />
  )
}

import { Toaster } from 'sonner'

/**
 * The application's only toast viewport. Mounted once in `main.tsx`; every
 * dashboard shares it through `lib/notifications/notification.ts`.
 *
 * The `app-toast` class applies the design-system card, status accent and
 * close button from `styles/toasts.css`.
 */
export function NotificationProvider() {
  return (
    <Toaster
      theme="dark"
      position="top-right"
      closeButton
      // Older toasts collapse behind the newest so feedback never covers
      // the page header controls; hovering expands the stack.
      visibleToasts={3}
      // Clear the 68px workspace top bar so header controls stay usable.
      offset={{ top: 80, right: 16 }}
      mobileOffset={{ top: 76, left: 16, right: 16 }}
      containerAriaLabel="Notifications"
      toastOptions={{
        closeButtonAriaLabel: 'Dismiss notification',
        classNames: { toast: 'app-toast' },
      }}
    />
  )
}

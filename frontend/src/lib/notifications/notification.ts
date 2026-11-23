import { toast, type ExternalToast } from 'sonner'
import { describeFailure, isSilentFailure } from './notificationErrors.ts'
import type {
  NotificationId,
  NotificationOptions,
  NotificationVariant,
  PromiseMessage,
  PromiseNotificationMessages,
} from './notification.types.ts'

/**
 * The single entry point for transient feedback. Components and hooks call
 * these helpers instead of importing Sonner, so styling, timing and duplicate
 * handling stay in one place. The matching `<Toaster>` is mounted once by
 * `providers/NotificationProvider.tsx`.
 *
 * Call success helpers only after the server has confirmed the change.
 */

const DEFAULT_DURATION = 4_000
const ERROR_DURATION = 7_000

function toastOptions(
  variant: NotificationVariant,
  message: string,
  description: string | undefined,
  options: NotificationOptions | undefined,
): ExternalToast {
  return {
    // Same variant + message replaces the visible toast instead of stacking.
    id: options?.id ?? `${variant}:${message}`,
    description,
    duration: options?.duration ?? (variant === 'error' ? ERROR_DURATION : DEFAULT_DURATION),
  }
}

function resolve<T>(message: PromiseMessage<T>, value: T): string {
  return typeof message === 'function' ? message(value) : message
}

export const notification = {
  success(message: string, description?: string, options?: NotificationOptions): NotificationId {
    return toast.success(message, toastOptions('success', message, description, options))
  },

  error(message: string, description?: string, options?: NotificationOptions): NotificationId {
    return toast.error(message, toastOptions('error', message, description, options))
  },

  warning(message: string, description?: string, options?: NotificationOptions): NotificationId {
    return toast.warning(message, toastOptions('warning', message, description, options))
  },

  info(message: string, description?: string, options?: NotificationOptions): NotificationId {
    return toast.info(message, toastOptions('info', message, description, options))
  },

  /** Shows a spinner toast that stays until it is updated or dismissed. */
  loading(message: string, options?: NotificationOptions): NotificationId {
    return toast.loading(message, {
      id: options?.id ?? `loading:${message}`,
      duration: options?.duration ?? Infinity,
    })
  },

  /**
   * Reports a failed request with a user-safe description. Cancelled requests
   * and expired sessions are skipped because the session boundary already
   * reports those. Returns null when nothing was shown.
   */
  requestFailed(message: string, error: unknown, options?: NotificationOptions): NotificationId | null {
    if (isSilentFailure(error)) return null
    return notification.error(message, describeFailure(error), options)
  },

  /**
   * Tracks a long-running operation in one toast: loading, then success or
   * error. Returns the original promise so callers keep their own handling.
   */
  promise<T>(promise: Promise<T>, messages: PromiseNotificationMessages<T>, options?: NotificationOptions): Promise<T> {
    const id = notification.loading(messages.loading, options)
    promise.then(
      (value) => {
        toast.success(resolve(messages.success, value), { id, duration: DEFAULT_DURATION })
      },
      (error: unknown) => {
        if (isSilentFailure(error)) {
          toast.dismiss(id)
          return
        }
        toast.error(resolve(messages.error, error), {
          id,
          description: describeFailure(error),
          duration: ERROR_DURATION,
        })
      },
    )
    return promise
  },

  /** Dismisses one toast, or every toast when no id is given. */
  dismiss(id?: NotificationId): void {
    toast.dismiss(id)
  },
}

export type NotificationService = typeof notification

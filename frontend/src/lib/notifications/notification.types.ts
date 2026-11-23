/**
 * Contracts for transient application feedback (toasts).
 *
 * These describe short-lived messages only. A future persistent notification
 * centre (bell, stored inbox) should add its own contracts instead of
 * stretching these; `NotificationVariant` and `NotificationContent` are the
 * shared vocabulary both could use.
 */

export type NotificationVariant = 'success' | 'error' | 'warning' | 'info' | 'loading'

/** Identifier of a displayed toast; pass it to `dismiss` or reuse it to update. */
export type NotificationId = string | number

export interface NotificationContent {
  /** Short headline, for example "Department created successfully". */
  message: string
  /** Optional supporting sentence shown under the headline. */
  description?: string
}

export interface NotificationOptions {
  /**
   * Stable identity. Showing a toast with an id that is already visible
   * replaces it instead of stacking a duplicate. Defaults to variant + message.
   */
  id?: NotificationId
  /** Milliseconds before auto-dismissal. Errors stay longer by default. */
  duration?: number
}

export type PromiseMessage<T> = string | ((value: T) => string)

export interface PromiseNotificationMessages<T> {
  loading: string
  success: PromiseMessage<T>
  /** Headline when the promise rejects; a safe description is added for API errors. */
  error: PromiseMessage<unknown>
}

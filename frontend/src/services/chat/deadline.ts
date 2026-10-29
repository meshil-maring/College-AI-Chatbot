export class ChatDeadlineError extends Error {
  constructor() {
    super('The chat request could not be confirmed before the timeout.')
    this.name = 'ChatDeadlineError'
  }
}

/** Bound the full fetch/body operation; caller cancellation also aborts its signal. */
export async function withDeadline<T>(
  milliseconds: number,
  operation: (signal: AbortSignal) => Promise<T>,
  externalSignal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController()
  const cancel = () => controller.abort()
  if (externalSignal?.aborted) controller.abort()
  externalSignal?.addEventListener('abort', cancel, { once: true })
  let expired = false
  const timer = setTimeout(() => {
    expired = true
    controller.abort()
  }, milliseconds)
  try {
    return await operation(controller.signal)
  } catch (error) {
    if (expired) throw new ChatDeadlineError()
    throw error
  } finally {
    clearTimeout(timer)
    externalSignal?.removeEventListener('abort', cancel)
  }
}

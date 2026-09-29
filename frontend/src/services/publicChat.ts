import type {
  PublicChatRequest,
  PublicChatResponse,
  PublicChatSource,
} from '../types/publicChat.ts'

const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
const PUBLIC_CHAT_ENDPOINT = `${API_BASE_URL}/v1/chat/public`
const PUBLIC_CHAT_TIMEOUT_MS = 35_000

export type PublicChatErrorKind =
  | 'validation'
  | 'institution'
  | 'auth_required'
  | 'timeout'
  | 'aborted'
  | 'network'
  | 'busy'
  | 'server'
  | 'malformed_response'
  | 'unknown'

export class PublicChatError extends Error {
  readonly kind: PublicChatErrorKind
  readonly status: number | null

  constructor(kind: PublicChatErrorKind, status: number | null = null) {
    super(publicChatErrorMessage(kind))
    this.name = 'PublicChatError'
    this.kind = kind
    this.status = status
  }
}

export function publicChatErrorMessage(kind: PublicChatErrorKind): string {
  switch (kind) {
    case 'validation':
      return 'Please enter a valid question and try again.'
    case 'institution':
      return 'This college chat is not available right now. Please check the link and try again.'
    case 'auth_required':
      return 'That information is private. Please sign in to access student-specific information.'
    case 'timeout':
      return 'The AI service took too long to respond. Please try again.'
    case 'aborted':
      return 'The request was cancelled.'
    case 'network':
      return 'Unable to connect to the AI service. Please check your connection and try again.'
    case 'busy':
      return 'The chatbot is busy right now. Please try again shortly.'
    case 'server':
    case 'malformed_response':
      return "Sorry, I couldn't process that question right now. Please try again."
    default:
      return 'Something went wrong. Please try again.'
  }
}

function isSource(value: unknown): value is PublicChatSource {
  if (typeof value !== 'object' || value === null) return false
  const source = value as Record<string, unknown>
  return (
    (typeof source.title === 'string' || source.title === null) &&
    (typeof source.section === 'string' || source.section === null) &&
    typeof source.quote === 'string'
  )
}

function isPublicChatResponse(value: unknown): value is PublicChatResponse {
  if (typeof value !== 'object' || value === null) return false
  const response = value as Record<string, unknown>
  if (response.status !== 'success' && response.status !== 'insufficient_context') return false
  if (typeof response.answer !== 'string' && response.answer !== null) return false
  if (!Array.isArray(response.sources) || !response.sources.every(isSource)) return false
  return response.status !== 'success' || (typeof response.answer === 'string' && response.answer.trim().length > 0)
}

function projectPublicResponse(value: PublicChatResponse): PublicChatResponse {
  return {
    answer: value.answer,
    status: value.status,
    sources: value.sources.map((source) => ({
      title: source.title,
      section: source.section,
      quote: source.quote,
    })),
  }
}

function classifyHttpError(status: number): PublicChatErrorKind {
  if (status === 401) return 'auth_required'
  if (status === 403 || status === 404) return 'institution'
  if (status === 400 || status === 413 || status === 422) return 'validation'
  if (status === 408 || status === 504) return 'timeout'
  if (status === 429 || status === 503) return 'busy'
  if (status >= 500) return 'server'
  return 'unknown'
}

/** Sends only the narrow anonymous request. No auth or internal controls exist here. */
export async function publicChat(
  request: PublicChatRequest,
  options: number | { timeoutMs?: number; signal?: AbortSignal } = PUBLIC_CHAT_TIMEOUT_MS,
): Promise<PublicChatResponse> {
  const timeoutMs = typeof options === 'number'
    ? options
    : (options.timeoutMs ?? PUBLIC_CHAT_TIMEOUT_MS)
  const externalSignal = typeof options === 'number' ? undefined : options.signal
  const controller = typeof AbortController === 'function' ? new AbortController() : null
  let timedOut = false
  const abortFromCaller = (): void => controller?.abort()
  if (externalSignal?.aborted) abortFromCaller()
  else externalSignal?.addEventListener('abort', abortFromCaller, { once: true })
  const timeoutId = controller === null ? null : setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  let response: Response

  try {
    response = await fetch(PUBLIC_CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        institution_code: request.institution_code,
        message: request.message,
      }),
      signal: controller?.signal,
    })
  } catch (error) {
    if (typeof error === 'object' && error !== null && 'name' in error && error.name === 'AbortError') {
      throw new PublicChatError(timedOut ? 'timeout' : 'aborted')
    }
    throw new PublicChatError('network')
  } finally {
    if (timeoutId !== null) clearTimeout(timeoutId)
    externalSignal?.removeEventListener('abort', abortFromCaller)
  }

  if (!response.ok) throw new PublicChatError(classifyHttpError(response.status), response.status)

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new PublicChatError('malformed_response', response.status)
  }
  if (!isPublicChatResponse(body)) {
    throw new PublicChatError('malformed_response', response.status)
  }
  // Project the allow-listed contract so unexpected backend fields can never
  // enter component state even if a future response accidentally adds them.
  return projectPublicResponse(body)
}

import type { PublicChatMessage, PublicChatSource } from '../../types/publicChat.ts'

export const PUBLIC_CHAT_STORAGE_PREFIX = 'college-ai-chatbot.public-chat.v1'
const MAX_MESSAGES = 40
const MAX_CONTENT_CHARS = 12_000
const MAX_SOURCES = 10

function storageKey(institutionCode: string): string {
  return `${PUBLIC_CHAT_STORAGE_PREFIX}:${institutionCode}`
}

function validSource(value: unknown): value is PublicChatSource {
  if (typeof value !== 'object' || value === null) return false
  const source = value as Record<string, unknown>
  return (
    (typeof source.title === 'string' || source.title === null) &&
    (typeof source.section === 'string' || source.section === null) &&
    typeof source.quote === 'string' && source.quote.length <= MAX_CONTENT_CHARS
  )
}

function validMessage(value: unknown): value is PublicChatMessage {
  if (typeof value !== 'object' || value === null) return false
  const message = value as Record<string, unknown>
  return (
    typeof message.id === 'string' &&
    (message.role === 'user' || message.role === 'assistant') &&
    typeof message.content === 'string' &&
    message.content.length <= MAX_CONTENT_CHARS &&
    typeof message.createdAt === 'number' &&
    Number.isFinite(message.createdAt) &&
    (message.status === undefined || message.status === 'success' || message.status === 'insufficient_context') &&
    (message.sources === undefined ||
      (Array.isArray(message.sources) &&
        message.sources.length <= MAX_SOURCES &&
        message.sources.every(validSource)))
  )
}

export function readPublicChatHistory(institutionCode: string): PublicChatMessage[] {
  try {
    const raw = window.localStorage.getItem(storageKey(institutionCode))
    if (raw === null) return []
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return []
    const envelope = parsed as Record<string, unknown>
    if (
      envelope.version !== 1 ||
      envelope.institutionCode !== institutionCode ||
      !Array.isArray(envelope.messages) ||
      envelope.messages.length > MAX_MESSAGES ||
      !envelope.messages.every(validMessage)
    ) return []
    return envelope.messages
  } catch {
    return []
  }
}

export function writePublicChatHistory(
  institutionCode: string,
  messages: PublicChatMessage[],
): void {
  const bounded = messages.slice(-MAX_MESSAGES)
  try {
    window.localStorage.setItem(storageKey(institutionCode), JSON.stringify({
      version: 1,
      institutionCode,
      messages: bounded,
    }))
  } catch {
    // Storage may be disabled or full; the in-memory conversation still works.
  }
}

export function clearPublicChatHistory(institutionCode: string): void {
  try {
    window.localStorage.removeItem(storageKey(institutionCode))
  } catch {
    // Clearing browser state remains best-effort when storage is unavailable.
  }
}

import type { PublicChatMessage, PublicChatSource, PublicConversation } from '../../../types/publicChat.ts'
export const PUBLIC_CHAT_STORAGE_PREFIX = 'college-ai-chatbot.public-chat.v2'

export const LEGACY_PUBLIC_CHAT_STORAGE_PREFIX = 'college-ai-chatbot.public-chat.v1'

export const PUBLIC_CHAT_MAX_MESSAGES = 40

export const PUBLIC_CHAT_MAX_STORAGE_CHARS = 256_000

export const STORAGE_VERSION = 2

export const MAX_USER_CONTENT_CHARS = 4_000

export const MAX_ASSISTANT_CONTENT_CHARS = 12_000

export const MAX_SOURCES = 10

export const MAX_SOURCE_FIELD_CHARS = 12_000

export const MAX_LOCAL_ID_CHARS = 128

export function record(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

export function hasOnlyKeys(value: Record<string, unknown>, allowed: readonly string[]): boolean {
  return Object.keys(value).every((key) => allowed.includes(key))
}

export function boundedString(value: unknown, max: number, nullable = false): boolean {
  return (nullable && value === null) || (typeof value === 'string' && value.length <= max)
}

export function validSource(value: unknown): value is PublicChatSource {
  const source = record(value)
  return (
    source !== null &&
    hasOnlyKeys(source, ['title', 'section', 'quote']) &&
    boundedString(source.title, MAX_SOURCE_FIELD_CHARS, true) &&
    boundedString(source.section, MAX_SOURCE_FIELD_CHARS, true) &&
    typeof source.quote === 'string' &&
    source.quote.length <= MAX_SOURCE_FIELD_CHARS
  )
}

export function validMessage(value: unknown): value is PublicChatMessage {
  const message = record(value)
  if (message === null || !hasOnlyKeys(message, ['id', 'role', 'content', 'status', 'sources', 'createdAt']))
    return false
  if (typeof message.id !== 'string' || message.id.length === 0 || message.id.length > MAX_LOCAL_ID_CHARS) return false
  if (message.role !== 'user' && message.role !== 'assistant') return false
  if (typeof message.content !== 'string' || message.content.length === 0) return false
  if (message.content.length > (message.role === 'user' ? MAX_USER_CONTENT_CHARS : MAX_ASSISTANT_CONTENT_CHARS))
    return false
  if (typeof message.createdAt !== 'number' || !Number.isFinite(message.createdAt) || message.createdAt < 0)
    return false
  if (message.status !== undefined && message.status !== 'success' && message.status !== 'insufficient_context')
    return false
  if (
    message.sources !== undefined &&
    (!Array.isArray(message.sources) || message.sources.length > MAX_SOURCES || !message.sources.every(validSource))
  )
    return false
  return message.role === 'assistant' || (message.status === undefined && message.sources === undefined)
}

export function validOrdering(messages: PublicChatMessage[]): boolean {
  return messages.every(
    (message, index) =>
      message.role === (index % 2 === 0 ? 'user' : 'assistant') &&
      (index === 0 || message.createdAt >= messages[index - 1].createdAt),
  )
}

export function canonicalMessage(message: PublicChatMessage): PublicChatMessage {
  return message.role === 'user'
    ? { id: message.id, role: 'user', content: message.content, createdAt: message.createdAt }
    : {
        id: message.id,
        role: 'assistant',
        content: message.content,
        ...(message.status === undefined ? {} : { status: message.status }),
        ...(message.sources === undefined
          ? {}
          : {
              sources: message.sources.map((source) => ({
                title: source.title,
                section: source.section,
                quote: source.quote,
              })),
            }),
        createdAt: message.createdAt,
      }
}

export function parseConversation(raw: string, institutionCode: string): PublicConversation | null {
  if (raw.length > PUBLIC_CHAT_MAX_STORAGE_CHARS) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null
  }
  const envelope = record(parsed)
  const conversation = record(envelope?.conversation)
  if (
    envelope === null ||
    conversation === null ||
    !hasOnlyKeys(envelope, ['version', 'conversation']) ||
    envelope.version !== STORAGE_VERSION ||
    !hasOnlyKeys(conversation, ['id', 'institutionCode', 'messages', 'createdAt', 'updatedAt']) ||
    typeof conversation.id !== 'string' ||
    conversation.id.length === 0 ||
    conversation.id.length > MAX_LOCAL_ID_CHARS ||
    conversation.institutionCode !== institutionCode ||
    !Array.isArray(conversation.messages) ||
    conversation.messages.length > PUBLIC_CHAT_MAX_MESSAGES ||
    !conversation.messages.every(validMessage) ||
    !validOrdering(conversation.messages) ||
    typeof conversation.createdAt !== 'number' ||
    !Number.isFinite(conversation.createdAt) ||
    conversation.createdAt < 0 ||
    typeof conversation.updatedAt !== 'number' ||
    !Number.isFinite(conversation.updatedAt) ||
    conversation.updatedAt < conversation.createdAt
  )
    return null
  return {
    id: conversation.id,
    institutionCode,
    messages: conversation.messages.map(canonicalMessage),
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
  }
}

export function parseLegacyConversation(raw: string, institutionCode: string): PublicConversation | null {
  if (raw.length > PUBLIC_CHAT_MAX_STORAGE_CHARS) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null
  }
  const envelope = record(parsed)
  if (
    envelope === null ||
    !hasOnlyKeys(envelope, ['version', 'institutionCode', 'messages']) ||
    envelope.version !== 1 ||
    envelope.institutionCode !== institutionCode ||
    !Array.isArray(envelope.messages) ||
    envelope.messages.length > PUBLIC_CHAT_MAX_MESSAGES ||
    !envelope.messages.every(validMessage) ||
    !validOrdering(envelope.messages)
  )
    return null
  const messages = envelope.messages.map(canonicalMessage)
  const createdAt = messages[0]?.createdAt ?? Date.now()
  return {
    id: localId(),
    institutionCode,
    messages,
    createdAt,
    updatedAt: messages.at(-1)?.createdAt ?? createdAt,
  }
}

export function localId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `public-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

import type {
  PublicChatMessage,
  PublicChatSource,
  PublicConversation,
} from '../../types/publicChat.ts'

export const PUBLIC_CHAT_STORAGE_PREFIX = 'college-ai-chatbot.public-chat.v2'
export const LEGACY_PUBLIC_CHAT_STORAGE_PREFIX = 'college-ai-chatbot.public-chat.v1'
export const PUBLIC_CHAT_MAX_MESSAGES = 40
export const PUBLIC_CHAT_MAX_STORAGE_CHARS = 256_000

const STORAGE_VERSION = 2
const MAX_USER_CONTENT_CHARS = 4_000
const MAX_ASSISTANT_CONTENT_CHARS = 12_000
const MAX_SOURCES = 10
const MAX_SOURCE_FIELD_CHARS = 12_000
const MAX_LOCAL_ID_CHARS = 128

export function normalizePublicInstitutionCode(institutionCode: string): string {
  return institutionCode.trim().toUpperCase()
}

export function publicChatStorageKey(institutionCode: string): string {
  return `${PUBLIC_CHAT_STORAGE_PREFIX}:${normalizePublicInstitutionCode(institutionCode)}`
}

function legacyStorageKey(institutionCode: string): string {
  return `${LEGACY_PUBLIC_CHAT_STORAGE_PREFIX}:${normalizePublicInstitutionCode(institutionCode)}`
}

function localId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `public-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function createPublicConversation(
  institutionCode: string,
  now: number = Date.now(),
): PublicConversation {
  return {
    id: localId(),
    institutionCode: normalizePublicInstitutionCode(institutionCode),
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function hasOnlyKeys(value: Record<string, unknown>, allowed: readonly string[]): boolean {
  return Object.keys(value).every((key) => allowed.includes(key))
}

function boundedString(value: unknown, max: number, nullable = false): boolean {
  return (nullable && value === null) || (typeof value === 'string' && value.length <= max)
}

function validSource(value: unknown): value is PublicChatSource {
  const source = record(value)
  return source !== null &&
    hasOnlyKeys(source, ['title', 'section', 'quote']) &&
    boundedString(source.title, MAX_SOURCE_FIELD_CHARS, true) &&
    boundedString(source.section, MAX_SOURCE_FIELD_CHARS, true) &&
    typeof source.quote === 'string' &&
    source.quote.length <= MAX_SOURCE_FIELD_CHARS
}

function validMessage(value: unknown): value is PublicChatMessage {
  const message = record(value)
  if (message === null || !hasOnlyKeys(message, [
    'id', 'role', 'content', 'status', 'sources', 'createdAt',
  ])) return false
  if (typeof message.id !== 'string' || message.id.length === 0 || message.id.length > MAX_LOCAL_ID_CHARS) return false
  if (message.role !== 'user' && message.role !== 'assistant') return false
  if (typeof message.content !== 'string' || message.content.length === 0) return false
  if (message.content.length > (message.role === 'user' ? MAX_USER_CONTENT_CHARS : MAX_ASSISTANT_CONTENT_CHARS)) return false
  if (typeof message.createdAt !== 'number' || !Number.isFinite(message.createdAt) || message.createdAt < 0) return false
  if (message.status !== undefined && message.status !== 'success' && message.status !== 'insufficient_context') return false
  if (message.sources !== undefined && (
    !Array.isArray(message.sources) ||
    message.sources.length > MAX_SOURCES ||
    !message.sources.every(validSource)
  )) return false
  return message.role === 'assistant' || (message.status === undefined && message.sources === undefined)
}

function validOrdering(messages: PublicChatMessage[]): boolean {
  return messages.every((message, index) =>
    message.role === (index % 2 === 0 ? 'user' : 'assistant') &&
    (index === 0 || message.createdAt >= messages[index - 1].createdAt),
  )
}

function canonicalMessage(message: PublicChatMessage): PublicChatMessage {
  return message.role === 'user'
    ? { id: message.id, role: 'user', content: message.content, createdAt: message.createdAt }
    : {
        id: message.id,
        role: 'assistant',
        content: message.content,
        ...(message.status === undefined ? {} : { status: message.status }),
        ...(message.sources === undefined ? {} : {
          sources: message.sources.map((source) => ({
            title: source.title,
            section: source.section,
            quote: source.quote,
          })),
        }),
        createdAt: message.createdAt,
      }
}

function parseConversation(raw: string, institutionCode: string): PublicConversation | null {
  if (raw.length > PUBLIC_CHAT_MAX_STORAGE_CHARS) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null
  }
  const envelope = record(parsed)
  const conversation = record(envelope?.conversation)
  if (envelope === null || conversation === null ||
    !hasOnlyKeys(envelope, ['version', 'conversation']) || envelope.version !== STORAGE_VERSION ||
    !hasOnlyKeys(conversation, ['id', 'institutionCode', 'messages', 'createdAt', 'updatedAt']) ||
    typeof conversation.id !== 'string' || conversation.id.length === 0 || conversation.id.length > MAX_LOCAL_ID_CHARS ||
    conversation.institutionCode !== institutionCode ||
    !Array.isArray(conversation.messages) || conversation.messages.length > PUBLIC_CHAT_MAX_MESSAGES ||
    !conversation.messages.every(validMessage) || !validOrdering(conversation.messages) ||
    typeof conversation.createdAt !== 'number' || !Number.isFinite(conversation.createdAt) || conversation.createdAt < 0 ||
    typeof conversation.updatedAt !== 'number' || !Number.isFinite(conversation.updatedAt) ||
    conversation.updatedAt < conversation.createdAt) return null
  return {
    id: conversation.id,
    institutionCode,
    messages: conversation.messages.map(canonicalMessage),
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
  }
}

function parseLegacyConversation(raw: string, institutionCode: string): PublicConversation | null {
  if (raw.length > PUBLIC_CHAT_MAX_STORAGE_CHARS) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null
  }
  const envelope = record(parsed)
  if (envelope === null || !hasOnlyKeys(envelope, ['version', 'institutionCode', 'messages']) ||
    envelope.version !== 1 || envelope.institutionCode !== institutionCode ||
    !Array.isArray(envelope.messages) || envelope.messages.length > PUBLIC_CHAT_MAX_MESSAGES ||
    !envelope.messages.every(validMessage) || !validOrdering(envelope.messages)) return null
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

function removeItem(key: string): void {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // Browser storage may be disabled. In-memory state remains available.
  }
}

export function boundPublicChatMessages(messages: PublicChatMessage[]): PublicChatMessage[] {
  let bounded = messages.slice(-PUBLIC_CHAT_MAX_MESSAGES).map(canonicalMessage)
  if (bounded[0]?.role === 'assistant') bounded = bounded.slice(1)
  return bounded
}

export function readPublicConversation(institutionCode: string): PublicConversation {
  const normalized = normalizePublicInstitutionCode(institutionCode)
  const key = publicChatStorageKey(normalized)
  try {
    const raw = window.localStorage.getItem(key)
    if (raw !== null) {
      const conversation = parseConversation(raw, normalized)
      if (conversation !== null) return conversation
      removeItem(key)
      return createPublicConversation(normalized)
    }

    const oldKey = legacyStorageKey(normalized)
    const legacyRaw = window.localStorage.getItem(oldKey)
    if (legacyRaw !== null) {
      const migrated = parseLegacyConversation(legacyRaw, normalized)
      removeItem(oldKey)
      if (migrated !== null) {
        writePublicConversation(migrated)
        return migrated
      }
    }
  } catch {
    // Invalid, denied, or unavailable storage starts a clean local conversation.
  }
  return createPublicConversation(normalized)
}

export function writePublicConversation(conversation: PublicConversation): void {
  const normalized = normalizePublicInstitutionCode(conversation.institutionCode)
  const key = publicChatStorageKey(normalized)
  if (conversation.messages.length === 0) {
    removeItem(key)
    return
  }
  let messages = boundPublicChatMessages(conversation.messages)
  while (messages.length > 0) {
    const safeConversation: PublicConversation = {
      id: conversation.id,
      institutionCode: normalized,
      messages,
      createdAt: conversation.createdAt,
      updatedAt: conversation.updatedAt,
    }
    const serialized = JSON.stringify({ version: STORAGE_VERSION, conversation: safeConversation })
    if (serialized.length <= PUBLIC_CHAT_MAX_STORAGE_CHARS) {
      try {
        window.localStorage.setItem(key, serialized)
      } catch {
        // Quota or policy failures do not break the in-memory conversation.
      }
      return
    }
    messages = messages.slice(messages[1]?.role === 'assistant' ? 2 : 1)
  }
  removeItem(key)
}

export function clearPublicConversation(institutionCode: string): void {
  removeItem(publicChatStorageKey(institutionCode))
}

// Compatibility helpers retained for focused consumers from Phase 7.6.
export function readPublicChatHistory(institutionCode: string): PublicChatMessage[] {
  return readPublicConversation(institutionCode).messages
}

export function writePublicChatHistory(institutionCode: string, messages: PublicChatMessage[]): void {
  const conversation = createPublicConversation(institutionCode, messages[0]?.createdAt)
  conversation.messages = boundPublicChatMessages(messages)
  conversation.updatedAt = messages.at(-1)?.createdAt ?? conversation.createdAt
  writePublicConversation(conversation)
}

export const clearPublicChatHistory = clearPublicConversation

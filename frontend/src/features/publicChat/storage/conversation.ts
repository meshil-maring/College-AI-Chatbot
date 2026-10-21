import type { PublicChatMessage, PublicConversation } from '../../../types/publicChat.ts'
import {
  LEGACY_PUBLIC_CHAT_STORAGE_PREFIX,
  PUBLIC_CHAT_MAX_MESSAGES,
  PUBLIC_CHAT_MAX_STORAGE_CHARS,
  PUBLIC_CHAT_STORAGE_PREFIX,
  STORAGE_VERSION,
  canonicalMessage,
  localId,
  parseConversation,
  parseLegacyConversation,
} from './validation.ts'
export function normalizePublicInstitutionCode(institutionCode: string): string {
  return institutionCode.trim().toUpperCase()
}

export function publicChatStorageKey(institutionCode: string): string {
  return `${PUBLIC_CHAT_STORAGE_PREFIX}:${normalizePublicInstitutionCode(institutionCode)}`
}

export function legacyStorageKey(institutionCode: string): string {
  return `${LEGACY_PUBLIC_CHAT_STORAGE_PREFIX}:${normalizePublicInstitutionCode(institutionCode)}`
}

export function createPublicConversation(institutionCode: string, now: number = Date.now()): PublicConversation {
  return {
    id: localId(),
    institutionCode: normalizePublicInstitutionCode(institutionCode),
    messages: [],
    createdAt: now,
    updatedAt: now,
  }
}

export function removeItem(key: string): void {
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

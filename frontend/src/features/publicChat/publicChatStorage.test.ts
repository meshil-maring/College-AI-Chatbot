import { beforeEach, describe, expect, it } from 'vitest'
import type { PublicChatMessage, PublicConversation } from '../../types/publicChat.ts'
import {
  LEGACY_PUBLIC_CHAT_STORAGE_PREFIX,
  PUBLIC_CHAT_MAX_MESSAGES,
  PUBLIC_CHAT_MAX_STORAGE_CHARS,
  PUBLIC_CHAT_STORAGE_PREFIX,
  createPublicConversation,
  publicChatStorageKey,
  readPublicChatHistory,
  readPublicConversation,
  writePublicChatHistory,
  writePublicConversation,
} from './publicChatStorage.ts'

function turn(index: number, content = `message-${index}`): PublicChatMessage[] {
  const createdAt = index * 2 + 1
  return [
    { id: `user-${index}`, role: 'user', content, createdAt },
    {
      id: `assistant-${index}`,
      role: 'assistant',
      content: `answer-${index}`,
      createdAt: createdAt + 1,
      status: 'success',
      sources: [{ title: 'FAQ', section: null, quote: 'Public quote' }],
    },
  ]
}

describe('public chat local storage', () => {
  beforeEach(() => localStorage.clear())

  it('persists a strict browser-only conversation in a normalized institution namespace', () => {
    const messages = turn(0)
    writePublicChatHistory(' git ', messages)

    expect(readPublicChatHistory('GIT')).toEqual(messages)
    const raw = localStorage.getItem(`${PUBLIC_CHAT_STORAGE_PREFIX}:GIT`) ?? ''
    expect(raw).toContain('"version":2')
    expect(raw).toContain('"institutionCode":"GIT"')
    expect(raw).not.toMatch(/token|provider|institution_id|document_id|chunk_id|storage_path/i)
    expect(readPublicChatHistory('OTHER')).toEqual([])
  })

  it.each([
    ['invalid JSON', '{broken'],
    ['old schema', JSON.stringify({ version: 0, conversation: {} })],
    ['missing messages', JSON.stringify({
      version: 2,
      conversation: { id: 'c', institutionCode: 'GIT', createdAt: 1, updatedAt: 1 },
    })],
    ['unexpected fields', JSON.stringify({
      version: 2,
      conversation: {
        id: 'c', institutionCode: 'GIT', messages: [], createdAt: 1, updatedAt: 1,
        provider: 'private',
      },
    })],
    ['oversized raw data', 'x'.repeat(PUBLIC_CHAT_MAX_STORAGE_CHARS + 1)],
  ])('discards %s without throwing or exposing parsing details', (_label, raw) => {
    const key = publicChatStorageKey('GIT')
    localStorage.setItem(key, raw)
    expect(readPublicChatHistory('GIT')).toEqual([])
    expect(localStorage.getItem(key)).toBeNull()
  })

  it('bounds message count and serialized size while retaining the newest complete turns', () => {
    const conversation = createPublicConversation('GIT', 1)
    conversation.messages = Array.from({ length: 30 }, (_, index) => {
      const messages = turn(index, index === 29 ? '<script>alert(1)</script>' : 'x'.repeat(4000))
      messages[1] = {
        ...messages[1],
        content: index === 29 ? 'latest answer' : 'a'.repeat(12_000),
        sources: Array.from({ length: 10 }, () => ({
          title: 'FAQ', section: null, quote: 'q'.repeat(2_000),
        })),
      }
      return messages
    }).flat()
    conversation.updatedAt = 60
    writePublicConversation(conversation)

    const raw = localStorage.getItem(publicChatStorageKey('GIT')) ?? ''
    const restored = readPublicConversation('GIT')
    expect(raw.length).toBeLessThanOrEqual(PUBLIC_CHAT_MAX_STORAGE_CHARS)
    expect(restored.messages.length).toBeLessThanOrEqual(PUBLIC_CHAT_MAX_MESSAGES)
    expect(restored.messages[0]?.role).toBe('user')
    expect(restored.messages.at(-2)?.content).toBe('<script>alert(1)</script>')
    expect(restored.messages.at(-1)?.content).toBe('latest answer')
  })

  it('keeps simultaneous institution histories separate', () => {
    writePublicChatHistory('COLLEGE-A', turn(0, 'Question for A'))
    writePublicChatHistory('college-b', turn(1, 'Question for B'))

    expect(publicChatStorageKey('COLLEGE-A')).not.toBe(publicChatStorageKey('COLLEGE-B'))
    expect(readPublicChatHistory('COLLEGE-A').map((message) => message.content)).toContain('Question for A')
    expect(readPublicChatHistory('COLLEGE-A').map((message) => message.content)).not.toContain('Question for B')
    expect(readPublicChatHistory('COLLEGE-B').map((message) => message.content)).toContain('Question for B')
  })

  it('keeps same-institution last-writer data structurally valid across tab-like writes', () => {
    const tabOne = createPublicConversation('GIT', 1)
    tabOne.messages = turn(0, 'Tab one')
    tabOne.updatedAt = 2
    const tabTwo = createPublicConversation('GIT', 3)
    tabTwo.messages = turn(1, 'Tab two')
    tabTwo.updatedAt = 4

    writePublicConversation(tabOne)
    writePublicConversation(tabTwo)
    const restored = readPublicConversation('GIT')
    expect(restored.id).toBe(tabTwo.id)
    expect(restored.messages.map((message) => message.content)).toContain('Tab two')
    expect(restored.messages.map((message) => message.content)).not.toContain('Tab one')
  })

  it('migrates valid Phase 7.6 history once and rejects cross-institution envelopes', () => {
    const legacyKey = `${LEGACY_PUBLIC_CHAT_STORAGE_PREFIX}:GIT`
    localStorage.setItem(legacyKey, JSON.stringify({
      version: 1,
      institutionCode: 'GIT',
      messages: turn(0, '<img src=x onerror=alert(1)>'),
    }))
    expect(readPublicChatHistory('git')[0]?.content).toBe('<img src=x onerror=alert(1)>')
    expect(localStorage.getItem(legacyKey)).toBeNull()
    expect(localStorage.getItem(publicChatStorageKey('GIT'))).not.toBeNull()

    const wrongTenant: PublicConversation = {
      ...createPublicConversation('OTHER', 1),
      messages: turn(1),
      updatedAt: 4,
    }
    localStorage.setItem(publicChatStorageKey('GIT'), JSON.stringify({
      version: 2,
      conversation: wrongTenant,
    }))
    expect(readPublicChatHistory('GIT')).toEqual([])
  })
})

import { beforeEach, describe, expect, it } from 'vitest'
import type { PublicChatMessage } from '../../types/publicChat.ts'
import {
  PUBLIC_CHAT_STORAGE_PREFIX,
  readPublicChatHistory,
  writePublicChatHistory,
} from './publicChatStorage.ts'

describe('public chat local storage', () => {
  beforeEach(() => localStorage.clear())

  it('persists only the versioned per-institution message envelope', () => {
    const messages: PublicChatMessage[] = [{
      id: 'local-1', role: 'assistant', content: 'Public answer', createdAt: 1,
      status: 'success', sources: [{ title: 'FAQ', section: null, quote: 'Public quote' }],
    }]
    writePublicChatHistory('GIT', messages)

    expect(readPublicChatHistory('GIT')).toEqual(messages)
    const raw = localStorage.getItem(`${PUBLIC_CHAT_STORAGE_PREFIX}:GIT`) ?? ''
    expect(raw).toContain('"version":1')
    expect(raw).not.toMatch(/token|provider|institution_id|document_id/i)
    expect(readPublicChatHistory('OTHER')).toEqual([])
  })

  it('fails closed for corrupted, old-version, and oversized storage', () => {
    const key = `${PUBLIC_CHAT_STORAGE_PREFIX}:GIT`
    localStorage.setItem(key, '{broken')
    expect(readPublicChatHistory('GIT')).toEqual([])
    localStorage.setItem(key, JSON.stringify({ version: 0, institutionCode: 'GIT', messages: [] }))
    expect(readPublicChatHistory('GIT')).toEqual([])
    localStorage.setItem(key, JSON.stringify({ version: 1, institutionCode: 'GIT', messages: Array(41).fill({ id: 'x', role: 'user', content: 'x', createdAt: 1 }) }))
    expect(readPublicChatHistory('GIT')).toEqual([])
  })
})

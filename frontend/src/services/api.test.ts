/**
 * Phase 5.7 — API client tests for conversation history endpoints.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getConversationMessages, listConversations } from './api.ts'

describe('listConversations', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends GET to /api/v1/conversations with Authorization header', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200, headers: { 'content-type': 'application/json' } }),
    )

    const result = await listConversations('test-token')

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/conversations')
    expect(options.method).toBe('GET')
    expect(options.headers).toEqual({ Authorization: 'Bearer test-token' })
    expect(result).toEqual([])
  })

  it('returns typed conversation summaries on success', async () => {
    const mockFetch = vi.mocked(fetch)
    const conversations = [
      {
        conversation_id: '12345678-1234-1234-1234-123456789abc',
        title: 'Test conversation',
        status: 'active',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-02T00:00:00Z',
      },
    ]
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(conversations), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )

    const result = await listConversations('test-token')

    expect(result).toHaveLength(1)
    expect(result[0].conversation_id).toBe('12345678-1234-1234-1234-123456789abc')
    expect(result[0].title).toBe('Test conversation')
    expect(result[0].status).toBe('active')
  })

  it('returns empty array for 200 with no conversations', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )

    const result = await listConversations('test-token')

    expect(result).toEqual([])
  })

  it('throws ApiError with 401 for unauthorized', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(listConversations('invalid-token')).rejects.toThrow(ApiError)
    await expect(listConversations('invalid-token')).rejects.toMatchObject({
      status: 401,
    })
  })

  it('throws ApiError with 500 for server error', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Internal server error' }), {
        status: 500,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(listConversations('test-token')).rejects.toMatchObject({
      status: 500,
    })
  })
})

describe('getConversationMessages', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends GET to /api/v1/conversations/{id}/messages with Authorization header', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200, headers: { 'content-type': 'application/json' } }),
    )

    const conversationId = '12345678-1234-1234-1234-123456789abc'
    const result = await getConversationMessages(conversationId, 'test-token')

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`/api/v1/conversations/${conversationId}/messages`)
    expect(options.method).toBe('GET')
    expect(options.headers).toEqual({ Authorization: 'Bearer test-token' })
    expect(result).toEqual([])
  })

  it('returns typed message summaries on success', async () => {
    const mockFetch = vi.mocked(fetch)
    const messages = [
      {
        message_id: 'aaaaaaaa-1111-2222-3333-444444444444',
        conversation_id: '12345678-1234-1234-1234-123456789abc',
        message_sequence: 1,
        message_type: 'user',
        content_text: 'Hello',
        created_at: '2025-01-01T00:00:00Z',
      },
      {
        message_id: 'bbbbbbbb-1111-2222-3333-444444444444',
        conversation_id: '12345678-1234-1234-1234-123456789abc',
        message_sequence: 2,
        message_type: 'assistant',
        content_text: 'Hi there!',
        created_at: '2025-01-01T00:00:01Z',
      },
    ]
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(messages), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )

    const result = await getConversationMessages('12345678-1234-1234-1234-123456789abc', 'test-token')

    expect(result).toHaveLength(2)
    expect(result[0].message_type).toBe('user')
    expect(result[0].content_text).toBe('Hello')
    expect(result[1].message_type).toBe('assistant')
    expect(result[1].content_text).toBe('Hi there!')
  })

  it('throws ApiError with 404 for conversation not found', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Conversation not found' }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(
      getConversationMessages('nonexistent-id', 'test-token'),
    ).rejects.toMatchObject({
      status: 404,
    })
  })

  it('throws ApiError with 401 for unauthorized', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    )

    await expect(
      getConversationMessages('12345678-1234-1234-1234-123456789abc', 'invalid-token'),
    ).rejects.toMatchObject({
      status: 401,
    })
  })
})

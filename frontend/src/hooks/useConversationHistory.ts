/** Phase 5.7 — TanStack Query boundary for conversation history. */

import { useCallback, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, getConversationMessages, listConversations } from '../services/api.ts'
import { queryClient } from '../lib/queryClient.ts'
import type { ConversationSummary, MessageSummary } from '../types/conversation.ts'

const SESSION_EXPIRED_MESSAGE = 'Your session has expired or is no longer valid. Please sign out and sign in again.'
const PERMISSION_MESSAGE = 'You do not have permission to view these conversations. Please sign out and sign in again.'
const VALIDATION_MESSAGE = 'The server could not process the request. Please try again.'
const SERVER_MESSAGE = 'The server reported an error while loading your conversations. Please try again in a moment.'
const NETWORK_MESSAGE = 'Could not reach the server. Check that the backend is running, then try again.'

function historyErrorMessage(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) return SESSION_EXPIRED_MESSAGE
    if (caught.status === 403) return PERMISSION_MESSAGE
    if (caught.status === 422) return VALIDATION_MESSAGE
    if (caught.status === 404) return 'The selected conversation could not be found. It may have been removed.'
    if (caught.status >= 500) return SERVER_MESSAGE
    return caught.message
  }
  return NETWORK_MESSAGE
}

export interface ConversationHistoryState {
  readonly conversations: ConversationSummary[]
  readonly selectedConversationId: string | null
  readonly historyLoading: boolean
  readonly historyError: string | null
  readonly messagesLoading: boolean
  readonly messagesError: string | null
  readonly loadConversations: (accessToken: string) => Promise<void>
  readonly selectConversation: (conversationId: string, accessToken: string) => Promise<MessageSummary[]>
  readonly clearSelection: () => void
  readonly clearAll: () => void
}

export function useConversationHistory(): ConversationHistoryState {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [messagesError, setMessagesError] = useState<string | null>(null)

  const conversationsQuery = useQuery<ConversationSummary[], unknown>(
    {
      queryKey: ['conversations', accessToken],
      queryFn: () => listConversations(accessToken as string),
      enabled: false,
      retry: false,
    },
    queryClient,
  )
  const messagesQuery = useQuery<MessageSummary[], unknown>(
    {
      queryKey: ['conversation-messages', accessToken, selectedConversationId],
      queryFn: () => getConversationMessages(selectedConversationId as string, accessToken as string),
      enabled: false,
      retry: false,
    },
    queryClient,
  )

  const loadConversations = useCallback(async (token: string): Promise<void> => {
    setAccessToken(token)
    setHistoryError(null)
    try {
      await queryClient.fetchQuery({
        queryKey: ['conversations', token],
        queryFn: () => listConversations(token),
        staleTime: 0,
      })
    } catch (caught) {
      setHistoryError(historyErrorMessage(caught))
    }
  }, [])

  const selectConversation = useCallback(async (conversationId: string, token: string) => {
    setAccessToken(token)
    setSelectedConversationId(conversationId)
    setMessagesError(null)
    try {
      return await queryClient.fetchQuery({
        queryKey: ['conversation-messages', token, conversationId],
        queryFn: () => getConversationMessages(conversationId, token),
        staleTime: 0,
      })
    } catch (caught) {
      setMessagesError(historyErrorMessage(caught))
      if (caught instanceof ApiError && caught.status === 404) setSelectedConversationId(null)
      throw caught
    }
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedConversationId(null)
    setMessagesError(null)
  }, [])

  const clearAll = useCallback(() => {
    setSelectedConversationId(null)
    setHistoryError(null)
    setMessagesError(null)
    if (accessToken !== null) {
      queryClient.removeQueries({ queryKey: ['conversations', accessToken] })
      queryClient.removeQueries({ queryKey: ['conversation-messages', accessToken] })
    }
    setAccessToken(null)
  }, [accessToken])

  return {
    conversations: conversationsQuery.data ?? [],
    selectedConversationId,
    historyLoading: conversationsQuery.isFetching,
    historyError,
    messagesLoading: messagesQuery.isFetching,
    messagesError,
    loadConversations,
    selectConversation,
    clearSelection,
    clearAll,
  }
}

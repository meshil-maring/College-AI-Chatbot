/** Identity-scoped, cancellable conversation history without credentials in keys. */

import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '../services/chat/api.ts'
import { conversationListOptions, conversationMessagesOptions } from '../features/chat/state/conversationQueries.ts'
import { queryClient } from '../lib/queryClient.ts'
import type { ConversationSummary, MessageSummary } from '../types/conversation.ts'

function historyErrorMessage(failure: unknown): string {
  if (failure instanceof ApiError) {
    if (failure.status === 401)
      return 'Your session has expired or is no longer valid. Please sign out and sign in again.'
    if (failure.status === 403)
      return 'You do not have permission to view these conversations. Please sign out and sign in again.'
    if (failure.status === 404) return 'The selected conversation could not be found. It may have been removed.'
    if (failure.status === 422) return 'The server could not process the request. Please try again.'
    return 'The server reported an error while loading your conversations. Please try again in a moment.'
  }
  return 'Could not reach the server. Check that the backend is running, then try again.'
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

export function useConversationHistory(scope?: string): ConversationHistoryState {
  const instance = useId()
  const identity = scope ?? instance
  const live = useRef(identity)
  live.current = identity
  const mounted = useRef(true)
  const token = useRef('')
  const selection = useRef(0)
  const listing = useRef(0)
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [messagesError, setMessagesError] = useState<string | null>(null)
  const [denied, setDenied] = useState(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      selection.current += 1
      listing.current += 1
      for (const prefix of ['conversations', 'conversation-messages']) {
        void queryClient.cancelQueries({ queryKey: [prefix, identity] })
        queryClient.removeQueries({ queryKey: [prefix, identity] })
      }
    }
  }, [identity])
  const conversationsQuery = useQuery(
    {
      ...conversationListOptions(identity, token.current),
      enabled: false,
      retry: false,
    },
    queryClient,
  )
  const messagesQuery = useQuery(
    {
      ...conversationMessagesOptions(identity, selectedConversationId ?? '', token.current),
      enabled: false,
      retry: false,
    },
    queryClient,
  )
  const loadConversations = useCallback(
    async (credential: string) => {
      token.current = credential
      const request = ++listing.current
      const valid = () =>
        mounted.current && live.current === identity && token.current === credential && listing.current === request
      setHistoryError(null)
      try {
        await queryClient.fetchQuery(conversationListOptions(identity, credential))
        if (valid()) {
          setDenied(false)
          setHistoryError(null)
        }
      } catch (failure) {
        if (!valid()) return
        setHistoryError(historyErrorMessage(failure))
        if (failure instanceof ApiError && [401, 403].includes(failure.status)) {
          setDenied(true)
          queryClient.removeQueries({ queryKey: ['conversations', identity] })
        }
      }
    },
    [identity],
  )
  const selectConversation = useCallback(
    async (id: string, credential: string) => {
      token.current = credential
      const request = ++selection.current
      setSelectedConversationId(id)
      setMessagesError(null)
      try {
        const messages = await queryClient.fetchQuery(conversationMessagesOptions(identity, id, credential))
        if (!mounted.current || live.current !== identity || request !== selection.current) {
          throw new DOMException('Retired conversation selection', 'AbortError')
        }
        return messages
      } catch (failure) {
        if (mounted.current && live.current === identity && request === selection.current) {
          setMessagesError(historyErrorMessage(failure))
          if (failure instanceof ApiError && failure.status === 404) setSelectedConversationId(null)
        }
        throw failure
      }
    },
    [identity],
  )
  const clearSelection = useCallback(() => {
    selection.current += 1
    setSelectedConversationId(null)
    setMessagesError(null)
  }, [])
  const clearAll = useCallback(() => {
    listing.current += 1
    clearSelection()
    setHistoryError(null)
    setDenied(false)
    for (const prefix of ['conversations', 'conversation-messages']) {
      void queryClient.cancelQueries({ queryKey: [prefix, identity] })
      queryClient.removeQueries({ queryKey: [prefix, identity] })
    }
    token.current = ''
  }, [identity, clearSelection])
  return {
    conversations: denied ? [] : (conversationsQuery.data ?? []),
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

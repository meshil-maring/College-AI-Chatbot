/** Shared chat state with identity guards and durable turn recovery. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '../features/auth/session/AuthProvider.tsx'
import { ApiError, chat } from '../services/chat/api.ts'
import { errorCode } from '../services/chat/recovery.ts'
import { queryClient } from '../lib/queryClient.ts'
import type { ChatRequest, ChatResponse, ResourceChatContext } from '../types/chat.ts'
import type { MessageSummary } from '../types/conversation.ts'
import type { ChatMessage } from '../features/chat/chatTypes.ts'
import {
  assistantMessage,
  chatErrorMessage,
  restoredMessages,
  userMessage,
} from '../features/chat/state/chatMessages.ts'
import { useTurnRecovery, type RecoveryState } from '../features/chat/recovery/useTurnRecovery.ts'

export interface ChatState {
  readonly messages: ChatMessage[]
  readonly isLoading: boolean
  readonly error: string | null
  readonly sessionId: string | null
  readonly conversationId: string | null
  readonly resourceContext: ResourceChatContext | null
  readonly blocked: boolean
  readonly recovery: RecoveryState | null
  readonly checkReply: () => Promise<void>
  readonly retryReply: () => Promise<void>
  readonly sendMessage: (raw: string) => Promise<void>
  readonly resetChat: () => void
  readonly loadConversation: (
    id: string,
    messages: MessageSummary[],
    resource?: ResourceChatContext | null,
    pendingTurn?: string | null,
  ) => void
}

export function useChat(initialResource: ResourceChatContext | null = null): ChatState {
  const { accessToken, user, sessionGeneration } = useAuth()
  const identity = JSON.stringify([
    sessionGeneration,
    user?.user_id,
    user?.institution_id,
    user?.role,
    [...(user?.effective_permissions ?? [])].sort(),
    initialResource?.knowledge_source_id,
  ])
  const current = useRef(identity)
  current.current = identity
  const mounted = useRef(true)
  const epoch = useRef(0)
  const pending = useRef(false)
  const [owner, setOwner] = useState(identity)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [resourceContext, setResourceContext] = useState(initialResource)
  const [blocked, setBlocked] = useState(false)
  const mutation = useMutation<ChatResponse, unknown, { request: ChatRequest; token: string }>(
    {
      mutationKey: ['chat', identity],
      mutationFn: ({ request, token }) => chat(request, token),
      retry: false,
    },
    queryClient,
  )

  function accept(response: ChatResponse, request: ChatRequest, recovered = false) {
    if (request.resource_id && response.resource_context?.knowledge_source_id !== request.resource_id) {
      throw new ApiError(409, 'Resource scope was not confirmed')
    }
    setSessionId(response.session_id)
    setConversationId(response.conversation_id)
    setResourceContext(response.resource_context ?? null)
    setMessages((previous) =>
      recovered && response.message_id && previous.some((message) => message.serverMessageId === response.message_id)
        ? previous
        : [...previous, assistantMessage(response)],
    )
    setBlocked(false)
    setError(null)
  }
  function deny(failure: unknown) {
    setError(chatErrorMessage(failure))
    setBlocked(true)
    setMessages([])
    setResourceContext((previous) => (previous ? { ...previous, title: null, available: false } : null))
  }
  const recovery = useTurnRecovery(identity, accessToken, (response, request) => accept(response, request, true), deny)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      epoch.current += 1
    }
  }, [])
  const resetChat = useCallback(() => {
    epoch.current += 1
    pending.current = false
    setOwner(identity)
    setMessages([])
    setSessionId(null)
    setConversationId(null)
    setResourceContext((previous) =>
      previous?.available === false && previous.knowledge_source_id === initialResource?.knowledge_source_id
        ? previous
        : initialResource,
    )
    setError(null)
    setBlocked(false)
    recovery.clear()
    mutation.reset()
  }, [identity, initialResource, mutation.reset])
  useEffect(() => {
    if (owner !== identity) resetChat()
  }, [owner, identity, resetChat])

  const perform = useCallback(
    async (request: ChatRequest, addQuestion: boolean) => {
      if (pending.current || blocked || resourceContext?.available === false) return
      if (!accessToken || !user?.institution_id) {
        setError('Sign in to an institution to continue chatting.')
        return
      }
      pending.current = true
      const operation = ++epoch.current
      const valid = () => mounted.current && current.current === identity && epoch.current === operation
      setError(null)
      recovery.clear()
      setSessionId(request.session_id ?? null)
      if (addQuestion) setMessages((previous) => [...previous, userMessage(request.user_query)])
      try {
        const response = await mutation.mutateAsync({ request, token: accessToken })
        if (!valid()) return
        accept(response, request)
      } catch (failure) {
        if (!valid()) return
        const code = errorCode(failure)
        if (
          !(failure instanceof ApiError) ||
          failure.status === 0 ||
          failure.status >= 500 ||
          code === 'CHAT_TURN_PENDING' ||
          code === 'CHAT_TURN_REPLACED'
        ) {
          recovery.remember(request)
        } else if (code === 'CHAT_TURN_BUSY') {
          setBlocked(true)
          setError('A previous reply is unfinished. Open this conversation from history to recover it.')
          if (addQuestion) setMessages((previous) => previous.slice(0, -1))
        } else if (resourceContext || [403, 404, 409].includes(failure.status)) {
          deny(failure)
        } else {
          setError(chatErrorMessage(failure))
        }
      } finally {
        if (valid()) {
          pending.current = false
          mutation.reset()
        }
      }
    },
    [accessToken, user?.institution_id, identity, resourceContext, blocked, mutation, recovery],
  )

  const sendMessage = useCallback(
    async (raw: string) => {
      const query = raw.trim()
      if (!query || recovery.state || pending.current || blocked) return
      const request: ChatRequest = {
        user_query: query,
        institution_id: user?.institution_id ?? '',
        session_id: sessionId ?? conversationId ?? crypto.randomUUID(),
        conversation_id: conversationId,
        turn_id: crypto.randomUUID(),
        ...(resourceContext ? { resource_id: resourceContext.knowledge_source_id } : {}),
      }
      await perform(request, true)
    },
    [perform, recovery.state, blocked, user?.institution_id, sessionId, conversationId, resourceContext],
  )

  const retryReply = async () => {
    if (recovery.state?.retryable && recovery.state.request) await perform(recovery.state.request, false)
  }
  const loadConversation = useCallback(
    (
      id: string,
      saved: MessageSummary[],
      resource: ResourceChatContext | null = null,
      pendingTurn: string | null = null,
    ) => {
      epoch.current += 1
      pending.current = false
      recovery.clear()
      setOwner(identity)
      setMessages(restoredMessages(saved))
      setConversationId(id)
      setSessionId(null)
      setResourceContext(resource)
      setBlocked(resource?.available === false)
      setError(null)
      mutation.reset()
      if (pendingTurn && resource?.available !== false) recovery.restore(pendingTurn)
    },
    [identity, mutation.reset, recovery.restore],
  )

  const visible = owner === identity
  return {
    messages: visible ? messages : [],
    isLoading: visible && mutation.isPending,
    error: visible ? error : null,
    sessionId: visible ? sessionId : null,
    conversationId: visible ? conversationId : null,
    resourceContext: visible ? resourceContext : initialResource,
    blocked: visible && blocked,
    recovery: visible ? recovery.state : null,
    checkReply: recovery.check,
    retryReply,
    sendMessage,
    resetChat,
    loadConversation,
  }
}

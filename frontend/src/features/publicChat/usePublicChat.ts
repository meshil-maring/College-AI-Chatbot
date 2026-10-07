import { useMutation } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { queryClient } from '../../lib/queryClient.ts'
import { PublicChatError, publicChat, publicChatErrorMessage } from '../../services/publicChat.ts'
import type { PublicChatMessage, PublicChatResponse, PublicConversation } from '../../types/publicChat.ts'
import {
  boundPublicChatMessages,
  clearPublicConversation,
  createPublicConversation,
  normalizePublicInstitutionCode,
  readPublicConversation,
  writePublicConversation,
} from './publicChatStorage.ts'

const INSUFFICIENT_CONTEXT_MESSAGE =
  "I couldn't find reliable public college information to answer that question."
const INTERRUPTED_REQUEST_MESSAGE =
  'The previous request was interrupted. Retry to continue this conversation.'

function unansweredUserId(conversation: PublicConversation): string | null {
  const last = conversation.messages.at(-1)
  return last?.role === 'user' ? last.id : null
}

function localId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `public-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function assistantMessage(response: PublicChatResponse): PublicChatMessage {
  return {
    id: localId(),
    role: 'assistant',
    content: response.status === 'success' ? response.answer! : INSUFFICIENT_CONTEXT_MESSAGE,
    status: response.status,
    sources: response.sources,
    createdAt: Date.now(),
  }
}

function appendMessage(
  conversation: PublicConversation,
  message: PublicChatMessage,
): PublicConversation {
  return {
    ...conversation,
    messages: boundPublicChatMessages([...conversation.messages, message]),
    updatedAt: message.createdAt,
  }
}

export function usePublicChat(institutionCode: string) {
  const normalizedCode = normalizePublicInstitutionCode(institutionCode)
  const [conversation, setConversation] = useState<PublicConversation>(() =>
    readPublicConversation(normalizedCode),
  )
  const initialUnansweredUserId = unansweredUserId(conversation)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(() =>
    initialUnansweredUserId === null ? null : INTERRUPTED_REQUEST_MESSAGE,
  )
  const [failedMessageId, setFailedMessageId] = useState<string | null>(initialUnansweredUserId)
  const answerMutation = useMutation<
    PublicChatResponse,
    unknown,
    { response: Promise<PublicChatResponse> }
  >(
    {
      mutationKey: ['public-chat', normalizedCode],
      mutationFn: ({ response }) => response,
    },
    queryClient,
  )
  const inFlight = useRef(false)
  const abortController = useRef<AbortController | null>(null)
  const activeInstitution = useRef(normalizedCode)

  useEffect(() => {
    activeInstitution.current = normalizedCode
    abortController.current?.abort()
    abortController.current = null
    inFlight.current = false
    setIsLoading(false)
    const nextConversation = readPublicConversation(normalizedCode)
    const unansweredId = unansweredUserId(nextConversation)
    setError(unansweredId === null ? null : INTERRUPTED_REQUEST_MESSAGE)
    setFailedMessageId(unansweredId)
    setConversation(nextConversation)
  }, [normalizedCode])

  useEffect(() => {
    if (conversation.institutionCode === normalizedCode) {
      writePublicConversation(conversation)
    }
  }, [conversation, normalizedCode])

  useEffect(() => () => {
    activeInstitution.current = ''
    abortController.current?.abort()
  }, [])

  const requestAnswer = useCallback(async (userMessage: PublicChatMessage): Promise<void> => {
    if (inFlight.current) return
    const requestInstitution = normalizedCode
    const controller = new AbortController()
    abortController.current = controller
    inFlight.current = true
    setIsLoading(true)
    setError(null)
    setFailedMessageId(null)
    try {
      // Start the request before entering the mutation scheduler so the
      // existing duplicate-submit UX remains synchronous. TanStack Query then
      // owns the mutation lifecycle and error boundary for the promise.
      const responsePromise = publicChat({
        institution_code: requestInstitution,
        message: userMessage.content,
      }, { signal: controller.signal })
      const response = await answerMutation.mutateAsync({ response: responsePromise })
      if (!controller.signal.aborted && activeInstitution.current === requestInstitution) {
        setConversation((current) => appendMessage(current, assistantMessage(response)))
      }
    } catch (reason) {
      const kind = reason instanceof PublicChatError ? reason.kind : 'unknown'
      if (kind !== 'aborted' && activeInstitution.current === requestInstitution) {
        setError(publicChatErrorMessage(kind))
        setFailedMessageId(userMessage.id)
      }
    } finally {
      if (abortController.current === controller) {
        abortController.current = null
        inFlight.current = false
        if (activeInstitution.current === requestInstitution) setIsLoading(false)
      }
    }
  }, [answerMutation, normalizedCode])

  const sendMessage = useCallback(async (raw: string): Promise<void> => {
    const content = raw.trim().replace(/\s+/g, ' ')
    if (inFlight.current || failedMessageId !== null || content.length === 0 || content.length > 4000) return
    const userMessage: PublicChatMessage = {
      id: localId(),
      role: 'user',
      content,
      createdAt: Date.now(),
    }
    setConversation((current) => appendMessage(current, userMessage))
    await requestAnswer(userMessage)
  }, [failedMessageId, requestAnswer])

  const retry = useCallback(async (): Promise<void> => {
    if (failedMessageId === null || inFlight.current) return
    const failed = conversation.messages.find(
      (message) => message.id === failedMessageId && message.role === 'user',
    )
    if (failed) await requestAnswer(failed)
  }, [conversation.messages, failedMessageId, requestAnswer])

  const reset = useCallback((): void => {
    if (inFlight.current) return
    clearPublicConversation(normalizedCode)
    setConversation(createPublicConversation(normalizedCode))
    setError(null)
    setFailedMessageId(null)
  }, [normalizedCode])

  return {
    conversation,
    messages: conversation.messages,
    isLoading,
    error,
    failedMessageId,
    sendMessage,
    retry,
    startNewConversation: reset,
    clear: reset,
  }
}

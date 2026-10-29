import { useMutation } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { queryClient } from '../../lib/queryClient.ts'
import { PublicChatError, publicChat, publicChatErrorMessage } from '../../services/chat/publicChat.ts'
import type { PublicChatMessage, PublicChatResponse, PublicConversation } from '../../types/publicChat.ts'
import { assistantMessage, appendMessage, unansweredUserId } from './state/messages.ts'
import { localId } from './storage/validation.ts'
import { useRetryDelay } from './recovery/useRetryDelay.ts'
import {
  clearPublicConversation,
  createPublicConversation,
  normalizePublicInstitutionCode,
  readPublicConversation,
  writePublicConversation,
} from './publicChatStorage.ts'

const INTERRUPTED_REQUEST_MESSAGE = 'The previous request was interrupted. Retry to continue this conversation.'

export function usePublicChat(institutionCode: string) {
  const normalizedCode = normalizePublicInstitutionCode(institutionCode)
  const retryDelay = useRetryDelay(normalizedCode)
  const [conversation, setConversation] = useState<PublicConversation>(() => readPublicConversation(normalizedCode))
  const initialUnansweredUserId = unansweredUserId(conversation)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(() =>
    initialUnansweredUserId === null ? null : INTERRUPTED_REQUEST_MESSAGE,
  )
  const [failedMessageId, setFailedMessageId] = useState<string | null>(initialUnansweredUserId)
  const answerMutation = useMutation<PublicChatResponse, unknown, { response: Promise<PublicChatResponse> }>(
    {
      mutationKey: ['public-chat', normalizedCode],
      mutationFn: ({ response }) => response,
      retry: false,
    },
    queryClient,
  )
  const inFlight = useRef(false)
  const abortController = useRef<AbortController | null>(null)
  const waitingQuestion = useRef<PublicChatMessage | null>(null)
  const activeInstitution = useRef(normalizedCode)

  useEffect(() => {
    activeInstitution.current = normalizedCode
    abortController.current?.abort()
    abortController.current = null
    waitingQuestion.current = null
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

  useEffect(
    () => () => {
      activeInstitution.current = ''
      abortController.current?.abort()
    },
    [],
  )

  const requestAnswer = useCallback(
    async (userMessage: PublicChatMessage): Promise<void> => {
      if (inFlight.current || retryDelay.blocked()) return
      const requestInstitution = normalizedCode
      const controller = new AbortController()
      abortController.current = controller
      waitingQuestion.current = userMessage
      const current = () =>
        abortController.current === controller &&
        !controller.signal.aborted &&
        activeInstitution.current === requestInstitution
      inFlight.current = true
      setIsLoading(true)
      setError(null)
      setFailedMessageId(null)
      try {
        // Start the request before entering the mutation scheduler so the
        // existing duplicate-submit UX remains synchronous. TanStack Query then
        // owns the mutation lifecycle and error boundary for the promise.
        const responsePromise = publicChat(
          {
            institution_code: requestInstitution,
            message: userMessage.content,
          },
          { signal: controller.signal },
        )
        const response = await answerMutation.mutateAsync({ response: responsePromise })
        if (current()) {
          setConversation((current) => appendMessage(current, assistantMessage(response)))
        }
      } catch (reason) {
        const kind = reason instanceof PublicChatError ? reason.kind : 'unknown'
        if (kind !== 'aborted' && current()) {
          setError(publicChatErrorMessage(kind))
          setFailedMessageId(userMessage.id)
          retryDelay.wait(reason instanceof PublicChatError ? reason.retryAfterSeconds : null)
        }
      } finally {
        if (abortController.current === controller) {
          abortController.current = null
          waitingQuestion.current = null
          inFlight.current = false
          if (activeInstitution.current === requestInstitution) setIsLoading(false)
        }
      }
    },
    [answerMutation, normalizedCode, retryDelay],
  )

  const stopWaiting = (): void => {
    const question = waitingQuestion.current
    if (!question) return
    abortController.current?.abort()
    abortController.current = null
    waitingQuestion.current = null
    inFlight.current = false
    setIsLoading(false)
    setFailedMessageId(question.id)
    setError('Stopped waiting for the reply. Your question is saved here; you can retry.')
    retryDelay.clear()
  }

  const sendMessage = useCallback(
    async (raw: string): Promise<void> => {
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
    },
    [failedMessageId, requestAnswer],
  )

  const retry = useCallback(async (): Promise<void> => {
    if (failedMessageId === null || inFlight.current) return
    const failed = conversation.messages.find((message) => message.id === failedMessageId && message.role === 'user')
    if (failed) await requestAnswer(failed)
  }, [conversation.messages, failedMessageId, requestAnswer])

  const reset = useCallback((): void => {
    if (inFlight.current) return
    clearPublicConversation(normalizedCode)
    setConversation(createPublicConversation(normalizedCode))
    setError(null)
    setFailedMessageId(null)
    retryDelay.clear()
  }, [normalizedCode, retryDelay])

  return {
    conversation,
    messages: conversation.messages,
    isLoading,
    error,
    failedMessageId,
    sendMessage,
    retry,
    stopWaiting,
    retryAfterSeconds: retryDelay.remaining,
    startNewConversation: reset,
    clear: reset,
  }
}

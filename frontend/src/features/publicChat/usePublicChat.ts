import { useCallback, useEffect, useRef, useState } from 'react'
import { PublicChatError, publicChat, publicChatErrorMessage } from '../../services/publicChat.ts'
import type { PublicChatMessage, PublicChatResponse } from '../../types/publicChat.ts'
import {
  clearPublicChatHistory,
  readPublicChatHistory,
  writePublicChatHistory,
} from './publicChatStorage.ts'

const INSUFFICIENT_CONTEXT_MESSAGE =
  "I couldn't find reliable public college information to answer that question."

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

export function usePublicChat(institutionCode: string) {
  const [messages, setMessages] = useState<PublicChatMessage[]>(() =>
    readPublicChatHistory(institutionCode),
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [failedMessageId, setFailedMessageId] = useState<string | null>(null)
  const inFlight = useRef(false)

  useEffect(() => {
    writePublicChatHistory(institutionCode, messages)
  }, [institutionCode, messages])

  const requestAnswer = useCallback(async (userMessage: PublicChatMessage): Promise<void> => {
    if (inFlight.current) return
    inFlight.current = true
    setIsLoading(true)
    setError(null)
    setFailedMessageId(null)
    try {
      const response = await publicChat({
        institution_code: institutionCode,
        message: userMessage.content,
      })
      setMessages((current) => [...current, assistantMessage(response)])
    } catch (reason) {
      const kind = reason instanceof PublicChatError ? reason.kind : 'unknown'
      setError(publicChatErrorMessage(kind))
      setFailedMessageId(userMessage.id)
    } finally {
      inFlight.current = false
      setIsLoading(false)
    }
  }, [institutionCode])

  const sendMessage = useCallback(async (raw: string): Promise<void> => {
    const content = raw.trim().replace(/\s+/g, ' ')
    if (inFlight.current || content.length === 0 || content.length > 4000) return
    const userMessage: PublicChatMessage = {
      id: localId(),
      role: 'user',
      content,
      createdAt: Date.now(),
    }
    setMessages((current) => [...current, userMessage])
    await requestAnswer(userMessage)
  }, [requestAnswer])

  const retry = useCallback(async (): Promise<void> => {
    if (failedMessageId === null || inFlight.current) return
    const failed = messages.find((message) => message.id === failedMessageId && message.role === 'user')
    if (failed) await requestAnswer(failed)
  }, [failedMessageId, messages, requestAnswer])

  const clear = useCallback((): void => {
    if (inFlight.current) return
    setMessages([])
    setError(null)
    setFailedMessageId(null)
    clearPublicChatHistory(institutionCode)
  }, [institutionCode])

  return { messages, isLoading, error, failedMessageId, sendMessage, retry, clear }
}

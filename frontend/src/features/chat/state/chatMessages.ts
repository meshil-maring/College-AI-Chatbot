import { ApiError } from '../../../services/chat/api.ts'
import type { ChatResponse } from '../../../types/chat.ts'
import type { MessageSummary } from '../../../types/conversation.ts'
import type { ChatMessage } from '../chatTypes.ts'

let nextMessageId = 1
export function userMessage(content: string): ChatMessage {
  return { id: `chat-msg-${nextMessageId++}`, role: 'user', content }
}
export function assistantMessage(response: ChatResponse): ChatMessage {
  return {
    ...userMessage(response.status === 'success' ? (response.answer ?? '(No answer text was returned.)') : ''),
    role: 'assistant',
    status: response.status,
    sources: response.sources,
    sourceReferences: response.source_references,
    usage: response.usage,
    modelUsed: response.model_used,
    serverMessageId: response.message_id ?? undefined,
  }
}
export function restoredMessages(messages: MessageSummary[]): ChatMessage[] {
  return messages.map((message) => ({
    ...userMessage(message.content_text),
    role: message.message_type === 'assistant' ? 'assistant' : 'user',
    serverMessageId: message.message_id,
    sources: message.message_type === 'assistant' ? (message.sources ?? []) : undefined,
  }))
}
export function chatErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Your session has expired. Please sign in again.'
    if (error.status === 403)
      return 'You do not have permission to continue this conversation. Please start a new chat.'
    if (error.status === 409) return 'Source access changed. Please start a new chat.'
    if (error.status === 422)
      return 'The server could not validate the request. Please check your question and try again.'
    return 'The chatbot server reported an error. Please try again in a moment.'
  }
  return 'Could not reach the chatbot server. Check your connection and start a new chat if the request was not confirmed.'
}

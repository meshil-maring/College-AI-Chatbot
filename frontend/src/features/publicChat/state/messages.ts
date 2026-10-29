import type { PublicChatMessage, PublicChatResponse, PublicConversation } from '../../../types/publicChat.ts'
import { boundPublicChatMessages } from '../publicChatStorage.ts'
import { localId } from '../storage/validation.ts'

export function unansweredUserId(conversation: PublicConversation): string | null {
  const last = conversation.messages.at(-1)
  return last?.role === 'user' ? last.id : null
}

export function assistantMessage(response: PublicChatResponse): PublicChatMessage {
  return {
    id: localId(),
    role: 'assistant',
    content:
      response.status === 'success'
        ? response.answer!
        : "I couldn't find reliable public college information to answer that question.",
    status: response.status,
    sources: response.sources,
    createdAt: Date.now(),
  }
}

export function appendMessage(conversation: PublicConversation, message: PublicChatMessage): PublicConversation {
  return {
    ...conversation,
    messages: boundPublicChatMessages([...conversation.messages, message]),
    updatedAt: message.createdAt,
  }
}

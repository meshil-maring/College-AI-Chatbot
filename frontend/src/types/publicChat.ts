/** Exact public HTTP contracts from backend/app/schemas/chat.py. */
export interface PublicChatRequest {
  institution_code: string
  message: string
}

export interface PublicChatSource {
  title: string | null
  section: string | null
  quote: string
}

export interface PublicChatResponse {
  answer: string | null
  status: 'success' | 'insufficient_context'
  sources: PublicChatSource[]
}

/** Browser-only presentation state. IDs never leave the browser. */
export interface PublicChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  status?: PublicChatResponse['status']
  sources?: PublicChatSource[]
  createdAt: number
}

/** Browser-local conversation state. The ID is never an authorization value or API field. */
export interface PublicConversation {
  id: string
  institutionCode: string
  messages: PublicChatMessage[]
  createdAt: number
  updatedAt: number
}

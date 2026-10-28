/**
 * Phase 5.5/5.7 — Chat shell.
 *
 * The authenticated application experience. Integrates the Phase 5.5 chat
 * interface with Phase 5.7 persisted conversation history:
 *   - College AI Chatbot branding
 *   - conversation history sidebar (Phase 5.7)
 *   - chat history (messages)
 *   - input + send
 *   - loading state
 *   - errors
 *   - sources
 *   - usage / model metadata
 *   - "New chat" control
 *
 * Auth state and the access token come exclusively from the Phase 5.4
 * AuthProvider. Chat state comes from the useChat hook, which talks to the
 * backend only through the Phase 5.3/5.7 api.ts client. History state comes
 * from the useConversationHistory hook.
 */

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { useChat } from '../../hooks/useChat.ts'
import { useConversationHistory } from '../../hooks/useConversationHistory.ts'
import ChatInput from './ChatInput.tsx'
import ChatHeader from './ChatHeader.tsx'
import MessageList from './MessageList.tsx'
import ConversationList from './ConversationList.tsx'

export default function ChatShell() {
  const { user, accessToken, logout } = useAuth()
  const { messages, isLoading, error, sendMessage, resetChat, loadConversation } = useChat()
  const {
    conversations,
    selectedConversationId,
    historyLoading,
    historyError,
    messagesLoading,
    messagesError,
    loadConversations,
    selectConversation,
    clearSelection,
    clearAll,
  } = useConversationHistory()

  const isAuthenticated = accessToken !== null
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (isAuthenticated && accessToken !== null) {
      void loadConversations(accessToken)
    }
  }, [isAuthenticated, accessToken, loadConversations])

  const handleLogout = useCallback(() => {
    clearAll()
    clearSelection()
    resetChat()
    logout()
  }, [clearAll, clearSelection, resetChat, logout])

  const handleSelectConversation = useCallback(
    async (conversationId: string) => {
      if (accessToken === null) return
      try {
        const historyMessages = await selectConversation(conversationId, accessToken)
        loadConversation(conversationId, historyMessages)
        setSidebarOpen(false)
      } catch {
        // Error state is managed by useConversationHistory
      }
    },
    [accessToken, selectConversation, loadConversation],
  )

  const handleNewChat = useCallback(() => {
    clearSelection()
    resetChat()
    setSidebarOpen(false)
  }, [clearSelection, resetChat])

  const handleSend = useCallback(
    (text: string) => {
      void sendMessage(text).then(() => {
        if (accessToken !== null) {
          void loadConversations(accessToken)
        }
      })
    },
    [sendMessage, accessToken, loadConversations],
  )

  return (
    <div className="ui-chat relative">
      <ChatHeader
        email={user?.email ?? undefined}
        busy={isLoading}
        historyOpen={sidebarOpen}
        onToggleHistory={() => setSidebarOpen(!sidebarOpen)}
        onNewChat={handleNewChat}
        onSignOut={handleLogout}
      />

      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen ? (
          <div
            className="absolute inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        ) : null}

        <aside
          className={`absolute inset-y-0 left-0 z-50 w-72 transform border-r border-line bg-surface transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 lg:transform-none ${
            sidebarOpen ? 'translate-x-0 visible' : '-translate-x-full invisible lg:visible'
          }`}
          aria-label="Conversation history sidebar"
        >
          <div className="flex h-full flex-col">
            <div className="border-b border-line px-4 py-3 lg:hidden">
              <h2 className="font-semibold text-content text-section">Conversations</h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              <div className="border-b border-line p-2 lg:hidden">
                <button
                  type="button"
                  onClick={handleNewChat}
                  disabled={isLoading}
                  className="w-full rounded-lg border border-dashed border-control bg-surface px-3 py-2 text-sm font-medium text-content hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  + New chat
                </button>
              </div>
              <ConversationList
                conversations={conversations}
                selectedConversationId={selectedConversationId}
                isLoading={historyLoading}
                error={historyError}
                onSelect={handleSelectConversation}
                onRetry={() => {
                  if (accessToken !== null) {
                    void loadConversations(accessToken)
                  }
                }}
              />
            </div>
          </div>
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          {error !== null ? (
            <div
              role="alert"
              className="mx-4 mt-3 rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger"
            >
              {error}
            </div>
          ) : null}

          {messagesError !== null ? (
            <div
              role="alert"
              className="mx-4 mt-3 rounded-lg border border-danger bg-danger-bg px-4 py-2 text-sm text-danger"
            >
              {messagesError}
            </div>
          ) : null}

          <main className="ui-chat-reading flex-1 overflow-y-auto px-4 py-4" aria-label="Chat conversation">
            <MessageList messages={messages} isLoading={isLoading || messagesLoading} />
          </main>

          <footer className="ui-chat-reading border-t border-line bg-surface px-4 py-4">
            {!isAuthenticated ? (
              <p role="alert" className="mb-2 text-xs text-danger">
                You are not authenticated. Please sign in to continue the chat.
              </p>
            ) : null}
            <ChatInput onSend={handleSend} disabled={isLoading || !isAuthenticated} />
          </footer>
        </div>
      </div>
    </div>
  )
}

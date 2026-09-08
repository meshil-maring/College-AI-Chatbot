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
import { useAuth } from '../auth/AuthProvider.tsx'
import { useChat } from '../../hooks/useChat.ts'
import { useConversationHistory } from '../../hooks/useConversationHistory.ts'
import ChatInput from './ChatInput.tsx'
import MessageList from './MessageList.tsx'
import ConversationList from './ConversationList.tsx'

export default function ChatShell() {
  const { user, accessToken, logout } = useAuth()
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    resetChat,
    loadConversation,
  } = useChat()
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
    <div className="h-screen bg-slate-900 flex flex-col">
      <header className="border-b border-slate-700 bg-slate-800/60 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label={sidebarOpen ? 'Close conversation history' : 'Open conversation history'}
            aria-expanded={sidebarOpen}
            className="lg:hidden rounded-lg border border-slate-600 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            {sidebarOpen ? 'Close' : 'History'}
          </button>
          <h1 className="text-lg font-bold text-white tracking-tight">
            College AI Chatbot
          </h1>
          <span className="rounded-full border border-emerald-700 bg-emerald-900/50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-300">
            Chat
          </span>
          {user?.email ? (
            <span className="text-xs text-slate-400">
              Signed in as {user.email}
            </span>
          ) : null}
          <div className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={handleNewChat}
              disabled={isLoading}
              className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              New chat
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen ? (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        ) : null}

        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-slate-700 bg-slate-900 transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 lg:transform-none ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          aria-label="Conversation history sidebar"
        >
          <div className="flex h-full flex-col">
            <div className="border-b border-slate-700 px-4 py-3 lg:hidden">
              <h2 className="text-sm font-semibold text-white">Conversations</h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              <div className="border-b border-slate-700 p-2 lg:hidden">
                <button
                  type="button"
                  onClick={handleNewChat}
                  disabled={isLoading}
                  className="w-full rounded-lg border border-dashed border-slate-600 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-emerald-400"
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
              className="mx-4 mt-3 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300"
            >
              {error}
            </div>
          ) : null}

          {messagesError !== null ? (
            <div
              role="alert"
              className="mx-4 mt-3 rounded-lg border border-red-900/50 bg-red-500/10 px-4 py-2 text-sm text-red-300"
            >
              {messagesError}
            </div>
          ) : null}

          <main
            className="flex-1 overflow-y-auto px-4 py-4"
            aria-label="Chat conversation"
          >
            <MessageList
              messages={messages}
              isLoading={isLoading || messagesLoading}
            />
          </main>

          <footer className="border-t border-slate-700 bg-slate-800/60 px-4 py-3">
            {!isAuthenticated ? (
              <p role="alert" className="mb-2 text-xs text-red-300">
                You are not authenticated. Please sign in to continue the chat.
              </p>
            ) : null}
            <ChatInput
              onSend={handleSend}
              disabled={isLoading || !isAuthenticated}
            />
          </footer>
        </div>
      </div>
    </div>
  )
}
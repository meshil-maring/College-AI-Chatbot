/** Conversation/history composition for one authenticated identity. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { useChat } from '../../../hooks/useChat.ts'
import { useConversationHistory } from '../../../hooks/useConversationHistory.ts'
import ChatInput from '../ChatInput.tsx'
import ChatHeader from '../ChatHeader.tsx'
import MessageList from '../MessageList.tsx'
import ConversationList from '../ConversationList.tsx'
import ResourceChatBanner from '../ResourceChatBanner.tsx'
import RecoveryNotice from '../recovery/RecoveryNotice.tsx'
import type { ResourceChatContext } from '../../../types/chat.ts'

export default function ChatSession({
  identity,
  initialResource,
}: {
  identity: string
  initialResource: ResourceChatContext | null
}) {
  const { user, accessToken, logout } = useAuth()
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    resetChat,
    loadConversation,
    resourceContext,
    blocked,
    recovery,
    checkReply,
    retryReply,
  } = useChat(initialResource)
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
  } = useConversationHistory(identity)
  const selectionEpoch = useRef(0)
  const active = useRef(true)
  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
    }
  }, [])

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
      const selected = conversations.find((row) => row.conversation_id === conversationId)
      if (!selected) return
      const operation = ++selectionEpoch.current
      loadConversation(conversationId, [], selected.resource_context ?? null)
      try {
        const historyMessages = await selectConversation(conversationId, accessToken)
        if (!active.current || selectionEpoch.current !== operation) return
        const resource = selected.resource_context
        const revoked = historyMessages.some((message) =>
          message.content_text.startsWith(
            'This part of the conversation is unavailable because source access changed.',
          ),
        )
        loadConversation(
          conversationId,
          historyMessages,
          resource && revoked ? { ...resource, title: null, available: false } : resource,
          selected.pending_turn_id,
        )
        setSidebarOpen(false)
      } catch {
        // Error state is managed by useConversationHistory
      }
    },
    [accessToken, conversations, selectConversation, loadConversation],
  )

  const handleNewChat = useCallback(() => {
    selectionEpoch.current += 1
    clearSelection()
    resetChat()
    setSidebarOpen(false)
  }, [clearSelection, resetChat])

  const refreshHistory = useCallback(() => {
    if (active.current && accessToken !== null) void loadConversations(accessToken)
  }, [accessToken, loadConversations])

  const handleSend = useCallback(
    (text: string) => {
      void sendMessage(text).then(refreshHistory)
    },
    [sendMessage, refreshHistory],
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
      <ResourceChatBanner resource={resourceContext} />

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
          <RecoveryNotice
            recovery={recovery}
            busy={isLoading}
            onCheck={() => void checkReply().then(refreshHistory)}
            onRetry={() => void retryReply().then(refreshHistory)}
          />

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
            <ChatInput
              key={selectedConversationId ?? 'new'}
              autoFocus={Boolean(initialResource)}
              onSend={handleSend}
              disabled={
                isLoading ||
                messagesLoading ||
                messagesError !== null ||
                blocked ||
                recovery !== null ||
                resourceContext?.available === false ||
                !isAuthenticated
              }
            />
          </footer>
        </div>
      </div>
    </div>
  )
}

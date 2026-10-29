import './mockSetup.ts'
import { screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as resources from '../../../services/knowledge/resources.ts'
import * as chatApi from '../../../services/chat/api.ts'
import { auth, server } from './mockSetup.ts'
import { openDraft, renderResources } from './support.tsx'

vi.mock('../../../services/chat/api.ts', async (original) => ({
  ...(await original<typeof import('../../../services/chat/api.ts')>()),
  chat: vi.fn(),
  listConversations: vi.fn(),
  getConversationMessages: vi.fn(),
}))
beforeEach(() => {
  vi.mocked(chatApi.listConversations).mockReset().mockResolvedValue([])
  vi.mocked(chatApi.getConversationMessages).mockReset().mockResolvedValue([])
  vi.mocked(chatApi.chat)
    .mockReset()
    .mockResolvedValue({
      session_id: 'session-a',
      conversation_id: 'chat-a',
      message_id: 'message-a',
      answer: 'Use the library card.',
      status: 'success',
      sources: [],
      source_references: [],
      model_used: null,
      metadata: {},
      usage: null,
      resource_context: {
        knowledge_source_id: server.library[0].knowledge_source_id,
        title: server.library[0].title,
        available: true,
      },
    })
})
async function openResource(user: ReturnType<typeof renderResources>['user']) {
  await user.click(await screen.findByRole('button', { name: 'View Published handbook' }))
  const dialog = await screen.findByRole('dialog')
  return within(dialog)
}

describe('Ask AI from Learning Resources', () => {
  it('confirms eligibility and opens the existing shared chat with a resource banner', async () => {
    const { user } = renderResources()
    const drawer = await openResource(user)
    await user.click(await drawer.findByRole('button', { name: 'Ask AI' }))
    expect(await screen.findByRole('region', { name: 'Resource conversation scope' })).toHaveTextContent(
      'Published handbook',
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Ask a question' }), 'How do I borrow?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Use the library card.')
    expect(chatApi.chat).toHaveBeenCalledWith(
      expect.objectContaining({
        resource_id: server.library[0].knowledge_source_id,
        institution_id: auth.user?.institution_id,
      }),
      'opaque-token',
    )
    await user.click(screen.getByRole('button', { name: 'Back to Learning Resources' }))
    expect(await screen.findByRole('heading', { name: 'Learning Resources' })).toBeInTheDocument()
  })
  it('offers no Ask AI action on a private draft or without the chat grant', async () => {
    const { user } = renderResources()
    const drawer = await openDraft(user)
    expect(drawer.queryByRole('button', { name: 'Ask AI' })).not.toBeInTheDocument()
  })
  it('hides the action when chat permission is absent', async () => {
    auth.user!.effective_permissions = ['documents.read']
    const { user } = renderResources()
    const drawer = await openResource(user)
    expect(drawer.queryByRole('button', { name: 'Ask AI' })).not.toBeInTheDocument()
  })
  it('does not open chat when the server rejects resource eligibility', async () => {
    vi.mocked(resources.getResourceChatContext).mockRejectedValueOnce(
      new resources.ResourceApiError(404, 'Private SQL detail'),
    )
    const { user } = renderResources()
    const drawer = await openResource(user)
    await user.click(await drawer.findByRole('button', { name: 'Ask AI' }))
    expect(await drawer.findByRole('alert')).toHaveTextContent('unavailable to AI')
    expect(screen.queryByRole('region', { name: 'Resource conversation scope' })).not.toBeInTheDocument()
    expect(screen.queryByText('Private SQL detail')).not.toBeInTheDocument()
  })
  it('restores a saved resource scope and can then select ordinary institution chat', async () => {
    const resource = {
      knowledge_source_id: server.library[0].knowledge_source_id,
      title: 'Saved guide',
      available: true,
    }
    vi.mocked(chatApi.listConversations).mockResolvedValue([
      {
        conversation_id: 'saved-a',
        title: 'Saved resource chat',
        status: 'active',
        created_at: '',
        updated_at: '',
        resource_context: resource,
      },
      {
        conversation_id: 'general-a',
        title: 'General chat',
        status: 'active',
        created_at: '',
        updated_at: '',
        resource_context: null,
      },
    ])
    const { user } = renderResources()
    const drawer = await openResource(user)
    await user.click(await drawer.findByRole('button', { name: 'Ask AI' }))
    await user.click(await screen.findByRole('button', { name: 'Saved resource chat' }))
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Resource conversation scope' })).toHaveTextContent('Saved guide'),
    )
    await user.type(screen.getByRole('textbox', { name: 'Ask a question' }), 'Continue')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await waitFor(() =>
      expect(chatApi.chat).toHaveBeenCalledWith(
        expect.objectContaining({
          conversation_id: 'saved-a',
          resource_id: resource.knowledge_source_id,
        }),
        'opaque-token',
      ),
    )
    await screen.findByText('Use the library card.')
    await user.click(screen.getByRole('button', { name: 'General chat' }))
    await waitFor(() =>
      expect(screen.queryByRole('region', { name: 'Resource conversation scope' })).not.toBeInTheDocument(),
    )
  })
})

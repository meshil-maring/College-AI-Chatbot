import './mockSetup.ts'
import * as api from '../../../services/knowledge/resources.ts'
import { act, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { auth } from './mockSetup.ts'
import { draft, user as identity } from './fixtures.ts'
import { openDraft, renderResources } from './support.tsx'

describe('resource identity boundaries', () => {
  it('preserves edits on token renewal and uses the current credential for the next save', async () => {
    const { user, replaceIdentity, client } = renderResources()
    const dialog = await openDraft(user)
    await user.type(dialog.getByRole('textbox', { name: 'Title' }), ' changed')
    auth.accessToken = 'renewed-secret'
    replaceIdentity()
    expect(screen.getByRole('textbox', { name: 'Title' })).toHaveValue('Library guide changed')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() =>
      expect(api.saveRevision).toHaveBeenCalledWith('renewed-secret', expect.anything(), expect.anything(), 4),
    )
    expect(
      JSON.stringify(
        client
          .getQueryCache()
          .getAll()
          .map((entry) => entry.queryKey),
      ),
    ).not.toContain('renewed-secret')
  })
  it('clears drafts and rejects late mutation callbacks after institution replacement', async () => {
    const { user, replaceIdentity, client } = renderResources()
    await screen.findByText('Published handbook')
    await user.click(screen.getByRole('button', { name: 'Add resource' }))
    await user.type(screen.getByRole('textbox', { name: 'Title' }), 'Private college A draft')
    let finish!: (result: ReturnType<typeof draft>) => void
    vi.mocked(api.createResource).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    auth.user = { ...identity(), institution_id: 'college-b', user_id: 'user-b' }
    auth.sessionGeneration += 1
    replaceIdentity()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => {
      finish(draft({ title: 'Private college A draft' }))
    })
    expect(screen.queryByText('Private college A draft')).not.toBeInTheDocument()
    expect(screen.queryByText('Changes saved.')).not.toBeInTheDocument()
    expect(
      client
        .getQueryCache()
        .getAll()
        .some((entry) => entry.queryKey[1]?.toString().includes('college-a')),
    ).toBe(false)
  })
  it('hides private content immediately after grants are replaced', async () => {
    const { user, replaceIdentity } = renderResources()
    await openDraft(user)
    auth.user = { ...identity(), effective_permissions: [] }
    replaceIdentity()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByText('Library guide')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('active institution account')
  })
  it('hides a cached resource workspace after a forbidden write', async () => {
    const { user } = renderResources()
    const dialog = await openDraft(user)
    await user.type(dialog.getByRole('textbox', { name: 'Title' }), ' updated')
    vi.mocked(api.saveRevision).mockRejectedValueOnce(new api.ResourceApiError(403, 'Revoked'))
    await user.click(dialog.getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('resource access changed')
    expect(screen.queryByText('Published handbook')).not.toBeInTheDocument()
  })
  it('does not discard drafts when the order of effective permissions changes', async () => {
    auth.user = { ...identity(), effective_permissions: ['documents.read', 'ai.knowledge.create', 'documents.create'] }
    const { user, replaceIdentity } = renderResources()
    await openDraft(user)
    await user.type(screen.getByRole('textbox', { name: 'Title' }), ' local')
    auth.user = { ...auth.user!, effective_permissions: ['documents.create', 'documents.read', 'ai.knowledge.create'] }
    replaceIdentity()
    expect(within(screen.getByRole('dialog')).getByRole('textbox', { name: 'Title' })).toHaveValue(
      'Library guide local',
    )
  })
})

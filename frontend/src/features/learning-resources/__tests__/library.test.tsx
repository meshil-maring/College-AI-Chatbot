import './mockSetup.ts'
import * as api from '../../../services/knowledge/resources.ts'
import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { auth, server } from './mockSetup.ts'
import { user as identity } from './fixtures.ts'
import { renderResources } from './support.tsx'

describe('shared resource library', () => {
  it.each(['admin', 'faculty', 'staff'] as const)('uses the same library and upload entry for %s', async (role) => {
    auth.user = identity(role)
    const { client } = renderResources()
    expect(await screen.findByRole('button', { name: 'View Published handbook' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Learning Resources', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add resource' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: 'Admin review' }) !== null).toBe(role === 'admin')
    expect(
      JSON.stringify(
        client
          .getQueryCache()
          .getAll()
          .map((query) => query.queryKey),
      ),
    ).not.toContain('opaque-token')
  })
  it('does not fetch when institution scope or resolved grants are missing', () => {
    auth.user = { ...identity(), institution_id: null }
    const { replaceIdentity } = renderResources()
    expect(screen.getByRole('status')).toHaveTextContent('active institution account')
    expect(api.listResources).not.toHaveBeenCalled()
    auth.user = { ...identity(), effective_permissions: [] }
    replaceIdentity()
    expect(api.listResources).not.toHaveBeenCalled()
  })
  it('shows loading and a retryable error without an empty-success flash', async () => {
    vi.mocked(api.listResources).mockRejectedValueOnce(new api.ResourceApiError(503, 'Unavailable'))
    const { user } = renderResources()
    expect(screen.getByRole('status', { name: 'Loading learning resources' })).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable')
    expect(screen.queryByText('No published resources yet')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add resource' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Retry loading resources' }))
    expect(await screen.findByText('Published handbook')).toBeInTheDocument()
  })
  it('retains authorized rows during a failed background refresh', async () => {
    const { user } = renderResources()
    await screen.findByText('Published handbook')
    vi.mocked(api.listResources).mockRejectedValueOnce(new api.ResourceApiError(500, 'Private failure'))
    await user.click(screen.getByRole('button', { name: 'Refresh', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Saved results could not be refreshed')
    expect(screen.getByText('Published handbook')).toBeInTheDocument()
    expect(screen.queryByText('Private failure')).not.toBeInTheDocument()
  })
  it('labels local filtering and clears it without inventing a server filter', async () => {
    const { user } = renderResources()
    await screen.findByText('Published handbook')
    await user.type(screen.getByRole('searchbox', { name: 'Search this page' }), 'no such resource')
    expect(screen.getByRole('heading', { name: 'No matches on this page' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByText('Published handbook')).toBeInTheDocument()
    expect(api.listResources).toHaveBeenCalledTimes(1)
  })
  it('removes cached source details when policy access changes to 404', async () => {
    const { user } = renderResources()
    await user.click(await screen.findByRole('button', { name: 'View Published handbook' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText('Official library information')).toBeInTheDocument()
    server.library = []
    vi.mocked(api.getResource).mockRejectedValueOnce(new api.ResourceApiError(404, 'Missing'))
    await user.click(within(dialog).getByRole('button', { name: 'Reload latest' }))
    await waitFor(() => expect(within(dialog).queryByText('Official library information')).not.toBeInTheDocument())
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('no longer available')
    expect(within(dialog).queryByText('guide.txt')).not.toBeInTheDocument()
  })
  it('keeps library-only grants read-only and hides draft/review actions', async () => {
    auth.user = { ...identity('staff'), effective_permissions: ['documents.read'] }
    renderResources()
    await screen.findByText('Published handbook')
    expect(screen.queryByRole('button', { name: 'Add resource' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'My submissions' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Admin review' })).not.toBeInTheDocument()
  })
})

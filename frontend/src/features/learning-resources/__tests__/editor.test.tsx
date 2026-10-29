import './mockSetup.ts'
import * as api from '../../../services/knowledge/resources.ts'
import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { server } from './mockSetup.ts'
import { renderResources, openDraft } from './support.tsx'
import { indexedFiles } from './fixtures.ts'

describe('resource draft and upload workflow', () => {
  it('creates a private draft with explicit student/teacher targets before accepting files', async () => {
    const { user } = renderResources()
    await screen.findByText('Published handbook')
    await user.click(screen.getByRole('button', { name: 'Add resource' }))
    const dialog = within(screen.getByRole('dialog'))
    await user.type(dialog.getByRole('textbox', { name: 'Title' }), 'New library rules')
    await user.click(dialog.getByRole('checkbox', { name: 'Students' }))
    await user.click(dialog.getByRole('checkbox', { name: 'Teachers' }))
    expect(dialog.queryByLabelText('Choose file')).not.toBeInTheDocument()
    await user.click(dialog.getByRole('button', { name: 'Save draft' }))
    expect(await dialog.findByLabelText('Choose file')).toBeInTheDocument()
    expect(api.createResource).toHaveBeenCalledWith(
      'opaque-token',
      expect.objectContaining({
        title: 'New library rules',
        audience: { mode: 'roles', roles: ['student', 'faculty'] },
      }),
    )
    expect(dialog.getByRole('button', { name: 'Submit for review' })).toBeDisabled()
    expect(api.decideRevision).not.toHaveBeenCalled()
  })
  it('keeps typed metadata after a rejected save and confirms unsaved close', async () => {
    const { user } = renderResources()
    const dialog = await openDraft(user)
    const title = dialog.getByRole('textbox', { name: 'Title' })
    await user.clear(title)
    await user.type(title, 'My unsaved proposal')
    vi.mocked(api.saveRevision).mockRejectedValueOnce(new api.ResourceApiError(422, 'Rejected'))
    await user.click(dialog.getByRole('button', { name: 'Save draft' }))
    expect(await dialog.findByRole('alert')).toBeInTheDocument()
    expect(title).toHaveValue('My unsaved proposal')
    await user.click(dialog.getByRole('button', { name: 'Close', exact: true }))
    const confirmation = within(screen.getByRole('alertdialog'))
    expect(confirmation.getByRole('button', { name: 'Keep editing' })).toHaveFocus()
    await user.click(confirmation.getByRole('button', { name: 'Keep editing' }))
    expect(screen.getByRole('textbox', { name: 'Title' })).toHaveValue('My unsaved proposal')
  })
  it('indexes a draft file and submits the returned revision version', async () => {
    const { user } = renderResources()
    const dialog = await openDraft(user)
    await user.upload(
      dialog.getByLabelText('Choose file'),
      new File(['Library text'], 'guide.txt', { type: 'text/plain' }),
    )
    await user.click(dialog.getByRole('button', { name: 'Upload and index' }))
    await waitFor(() => expect(dialog.getByRole('button', { name: 'Submit for review' })).toBeEnabled())
    await user.click(dialog.getByRole('button', { name: 'Submit for review' }))
    await user.click(dialog.getByRole('button', { name: 'Confirm submit for review' }))
    await waitFor(() =>
      expect(api.decideRevision).toHaveBeenCalledWith(
        'opaque-token',
        expect.objectContaining({ revision_version: 6 }),
        'submit',
        '',
      ),
    )
    expect(await dialog.findByText('Under review')).toBeInTheDocument()
    expect(dialog.queryByRole('button', { name: 'Publish revision' })).not.toBeInTheDocument()
  })
  it('recovers a saved upload with failed indexing without uploading another version', async () => {
    const { user } = renderResources()
    const dialog = await openDraft(user)
    vi.mocked(api.uploadResourceFile).mockImplementationOnce(async () => {
      server.revision = {
        ...server.revision,
        revision_version: 9,
        documents: indexedFiles().map((file) => ({ ...file, indexing_status: 'failed' })),
      }
      throw new api.ResourceApiError(422, 'Indexing failed', undefined, 'RESOURCE_INDEXING_FAILED')
    })
    await user.upload(
      dialog.getByLabelText('Choose file'),
      new File(['Library text'], 'guide.txt', { type: 'text/plain' }),
    )
    await user.click(dialog.getByRole('button', { name: 'Upload and index' }))
    await user.click(await dialog.findByRole('button', { name: 'Retry indexing guide.txt' }))
    await waitFor(() =>
      expect(api.retryResourceIndex).toHaveBeenCalledWith(
        'opaque-token',
        expect.objectContaining({ revision_version: 9 }),
        'version-a',
      ),
    )
    expect(api.uploadResourceFile).toHaveBeenCalledTimes(1)
    expect(await dialog.findByText('Indexed')).toBeInTheDocument()
  })
  it('keeps a stale edit until the user explicitly discards it and reloads', async () => {
    const { user } = renderResources()
    const dialog = await openDraft(user)
    const title = dialog.getByRole('textbox', { name: 'Title' })
    await user.clear(title)
    await user.type(title, 'Unsaved local proposal')
    vi.mocked(api.saveRevision).mockRejectedValueOnce(new api.ResourceApiError(409, 'Stale'))
    await user.click(dialog.getByRole('button', { name: 'Save draft' }))
    await dialog.findByRole('alert')
    expect(title).toHaveValue('Unsaved local proposal')
    expect(dialog.getByRole('button', { name: 'Save draft' })).toBeDisabled()
    server.revision = { ...server.revision, title: 'New server title', revision_version: 14 }
    await user.click(dialog.getByRole('button', { name: 'Reload latest' }))
    await user.click(screen.getByRole('button', { name: 'Discard entries and reload' }))
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Title' })).toHaveValue('New server title'))
    await user.type(screen.getByRole('textbox', { name: 'Title' }), ' updated')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() =>
      expect(api.saveRevision).toHaveBeenLastCalledWith('opaque-token', expect.anything(), expect.anything(), 14),
    )
  })
})

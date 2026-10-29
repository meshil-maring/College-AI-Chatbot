import './mockSetup.ts'
import * as api from '../../../services/knowledge/resources.ts'
import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { auth, server } from './mockSetup.ts'
import { draft, indexedFiles, user as identity } from './fixtures.ts'
import { renderResources } from './support.tsx'

describe('admin resource decisions', () => {
  it('approves and publishes only after explicit confirmation with current policy tokens', async () => {
    auth.user = identity('admin')
    server.revision = draft({ lifecycle_status: 'under_review', documents: indexedFiles(), policy_version: 2 })
    const { user } = renderResources()
    await user.click(await screen.findByRole('button', { name: 'Admin review' }))
    await user.click(await screen.findByRole('button', { name: 'View Library guide' }))
    const dialog = within(await screen.findByRole('dialog'))
    await user.click(await dialog.findByRole('button', { name: 'Approve revision' }))
    expect(api.decideRevision).not.toHaveBeenCalled()
    expect(dialog.getByRole('group', { name: 'Confirm resource decision' })).toHaveTextContent('Students')
    await user.click(dialog.getByRole('button', { name: 'Confirm approve revision' }))
    await waitFor(() => expect(dialog.getByRole('button', { name: 'Publish revision' })).toBeEnabled())
    await user.click(dialog.getByRole('button', { name: 'Publish revision' }))
    await user.click(dialog.getByRole('button', { name: 'Confirm publish revision' }))
    await waitFor(() =>
      expect(api.decideRevision).toHaveBeenLastCalledWith(
        'opaque-token',
        expect.objectContaining({ revision_version: 5, policy_version: 2 }),
        'publish',
        '',
      ),
    )
    expect(await dialog.findByText('Published')).toBeInTheDocument()
  })
  it('requires reviewer feedback to request changes', async () => {
    auth.user = identity('admin')
    server.revision = draft({ lifecycle_status: 'under_review', documents: indexedFiles() })
    const { user } = renderResources()
    await user.click(screen.getByRole('button', { name: 'Admin review' }))
    await user.click(await screen.findByRole('button', { name: 'View Library guide' }))
    const dialog = within(await screen.findByRole('dialog'))
    await waitFor(() => expect(dialog.getByRole('button', { name: 'Request changes' })).toBeDisabled())
    await user.type(dialog.getByRole('textbox', { name: 'Review feedback' }), 'Please correct the end date.')
    await user.click(dialog.getByRole('button', { name: 'Request changes' }))
    await user.click(dialog.getByRole('button', { name: 'Confirm request changes' }))
    await waitFor(() =>
      expect(api.decideRevision).toHaveBeenCalledWith(
        'opaque-token',
        expect.anything(),
        'request_changes',
        'Please correct the end date.',
      ),
    )
  })
  it('blocks repeated publication clicks and waits for server confirmation', async () => {
    auth.user = identity('admin')
    server.revision = draft({ lifecycle_status: 'approved', documents: indexedFiles() })
    let finish!: (revision: ReturnType<typeof draft>) => void
    vi.mocked(api.decideRevision).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const { user } = renderResources()
    await user.click(screen.getByRole('button', { name: 'Admin review' }))
    await user.click(await screen.findByRole('button', { name: 'View Library guide' }))
    const dialog = within(await screen.findByRole('dialog'))
    await user.click(await dialog.findByRole('button', { name: 'Publish revision' }))
    await user.dblClick(dialog.getByRole('button', { name: 'Confirm publish revision' }))
    expect(api.decideRevision).toHaveBeenCalledTimes(1)
    expect(dialog.queryByText('Published')).not.toBeInTheDocument()
    server.revision = { ...server.revision, lifecycle_status: 'published', revision_version: 5, policy_version: 1 }
    finish(structuredClone(server.revision))
    expect(await dialog.findByText('Published')).toBeInTheDocument()
  })
  it.each(['faculty', 'staff'] as const)('does not give %s publication controls through broad grants', async (role) => {
    auth.user = identity(role)
    server.revision = draft({ lifecycle_status: 'approved', documents: indexedFiles() })
    const { user } = renderResources()
    await user.click(screen.getByRole('button', { name: 'My submissions' }))
    await user.click(await screen.findByRole('button', { name: 'View Library guide' }))
    const dialog = within(await screen.findByRole('dialog'))
    await dialog.findByText('Approved')
    expect(screen.queryByRole('button', { name: 'Admin review' })).not.toBeInTheDocument()
    expect(dialog.queryByRole('button', { name: 'Publish revision' })).not.toBeInTheDocument()
    expect(dialog.queryByRole('button', { name: 'Request changes' })).not.toBeInTheDocument()
  })
})

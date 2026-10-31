import { auth, renderStructure } from './Structure.support.tsx'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const session = auth as typeof auth & { sessionGeneration?: number }
afterEach(() => {
  delete session.sessionGeneration
})

function workspace() {
  return <AcademicWorkspace page="curriculum-versions" search="" onNavigate={vi.fn()} onClearSearch={vi.fn()} />
}

async function openDraft() {
  const trigger = screen.getByRole('button', { name: 'Add Curriculum' })
  await waitFor(() => expect(trigger).toBeEnabled())
  fireEvent.click(trigger)
  fireEvent.change(screen.getByRole('textbox', { name: 'Curriculum Name' }), {
    target: { value: 'Unsaved semester draft' },
  })
}

describe('Academic draft lifetime', () => {
  it('keeps a draft when the same authenticated session rotates its access token', async () => {
    session.sessionGeneration = 1
    const view = renderStructure()
    await openDraft()
    auth.accessToken = 'rotated-provider-token'
    view.rerender(workspace())
    expect(screen.getByRole('textbox', { name: 'Curriculum Name' })).toHaveValue('Unsaved semester draft')
  })

  it('discards a draft when a fresh login replaces the session for the same account', async () => {
    session.sessionGeneration = 1
    const view = renderStructure()
    await openDraft()
    session.sessionGeneration = 2
    auth.accessToken = 'fresh-login-token'
    view.rerender(workspace())
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('discards a draft immediately when permissions change', async () => {
    session.sessionGeneration = 1
    const view = renderStructure()
    await openDraft()
    auth.user.effective_permissions = []
    view.rerender(workspace())
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
